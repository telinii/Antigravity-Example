import pygame
import random
import math
import sys

# ─────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────
LARGURA, ALTURA = 800, 600
FPS = 60
TITULO = "Space Shooter — Atari 2D"

# Cores
PRETO        = (0,   0,   0)
BRANCO       = (255, 255, 255)
CIANO        = (0,   230, 255)
AMARELO      = (255, 230,  50)
DOURADO      = (255, 200,   0)
CINZA        = (160, 160, 160)
CINZA_ESCURO = (80,  80,  80)
VERMELHO     = (220,  50,  50)
LARANJA      = (255, 140,   0)
VERDE        = (50,  220, 100)
ROXO         = (140,  60, 200)

# Nave
NAVE_VELOCIDADE   = 5
NAVE_LARGURA      = 40
NAVE_ALTURA       = 36
DISPARO_COOLDOWN  = 300   # ms

# Projétil
PROJ_VELOCIDADE   = 12
PROJ_LARGURA      = 4
PROJ_ALTURA       = 14

# Asteroides
ASTEROIDE_VEL_BASE   = 1.4
ASTEROIDE_INTERVALO  = 1200  # ms entre spawns
PONTOS_POR_ACERTO    = 10

# Buff
BUFF_DURACAO_MS          = 10_000   # 10 segundos
BUFF_CHANCE_SPAWN        = 0.20     # 20% de chance de ser asteroide buff
BUFF_ACERTOS_PERMANENTE  = 5        # acertos para tornar buff permanente
BUFF_VEL_BONUS           = 2        # bônus de velocidade da nave por buff ativo
BUFF_ANGULO_DIAGONAL     = 25       # graus de abertura dos tiros diagonais

# Estrelas (fundo)
NUM_ESTRELAS = 120


# ─────────────────────────────────────────────
#  UTILITÁRIOS
# ─────────────────────────────────────────────
def gerar_estrelas():
    """Gera pontos aleatórios para o fundo estrelado."""
    return [
        (random.randint(0, LARGURA),
         random.randint(0, ALTURA),
         random.randint(1, 3))
        for _ in range(NUM_ESTRELAS)
    ]


def calcular_velocidade_asteroide(pontuacao, tier=0):
    """Aumenta velocidade a cada 50 pontos + por tier permanente."""
    bonus_pts  = (pontuacao // 50) * 0.4
    bonus_tier = tier * 0.5
    return min(ASTEROIDE_VEL_BASE + bonus_pts + bonus_tier, 9.0)


def calcular_intervalo_spawn(pontuacao, tier=0):
    """Diminui o intervalo de spawn a cada 50 pontos + por tier permanente."""
    reducao_pts  = (pontuacao // 50) * 80
    reducao_tier = tier * 150
    return max(ASTEROIDE_INTERVALO - reducao_pts - reducao_tier, 300)


def desenhar_estrela_simbolo(superficie, cx, cy, raio, cor, n=5):
    """Desenha um símbolo ★ com n pontas centrado em (cx, cy)."""
    pontos = []
    raio_interno = raio * 0.45
    for i in range(n * 2):
        angulo = math.radians(-90 + i * (360 / (n * 2)))
        r = raio if i % 2 == 0 else raio_interno
        pontos.append((cx + r * math.cos(angulo), cy + r * math.sin(angulo)))
    pygame.draw.polygon(superficie, cor, pontos)


# ─────────────────────────────────────────────
#  CLASSE: NAVE
# ─────────────────────────────────────────────
class Nave:
    def __init__(self):
        self.x = LARGURA // 2
        self.y = ALTURA - 60
        self.largura = NAVE_LARGURA
        self.altura = NAVE_ALTURA
        self.ultimo_disparo = 0
        self.propulsor_anim = 0

    @property
    def rect(self):
        return pygame.Rect(
            self.x - self.largura // 2,
            self.y - self.altura // 2,
            self.largura,
            self.altura
        )

    def mover(self, teclas, velocidade):
        if teclas[pygame.K_LEFT]:
            self.x -= velocidade
        if teclas[pygame.K_RIGHT]:
            self.x += velocidade
        self.x = max(self.largura // 2, min(LARGURA - self.largura // 2, self.x))

    def pode_atirar(self):
        agora = pygame.time.get_ticks()
        return agora - self.ultimo_disparo >= DISPARO_COOLDOWN

    def atirar(self, com_buff=False):
        """Retorna lista de projéteis. com_buff=True dispara triplo."""
        self.ultimo_disparo = pygame.time.get_ticks()
        ox = self.x
        oy = self.y - self.altura // 2

        if not com_buff:
            return [Projetil(ox, oy, 0, -PROJ_VELOCIDADE)]

        # Tiro triplo: centro, diagonal esquerda, diagonal direita
        ang = math.radians(BUFF_ANGULO_DIAGONAL)
        return [
            Projetil(ox, oy,  0,                           -PROJ_VELOCIDADE),
            Projetil(ox, oy, -math.sin(ang) * PROJ_VELOCIDADE, -math.cos(ang) * PROJ_VELOCIDADE),
            Projetil(ox, oy,  math.sin(ang) * PROJ_VELOCIDADE, -math.cos(ang) * PROJ_VELOCIDADE),
        ]

    def desenhar(self, superficie, com_buff=False, tier=0):
        cx, cy = self.x, self.y
        hw = self.largura // 2
        hh = self.altura // 2

        self.propulsor_anim = (self.propulsor_anim + 5) % 360
        pulso = abs(math.sin(math.radians(self.propulsor_anim)))

        # Propulsor (chama) — dourado se com buff
        chama_h = int(10 + pulso * 12)
        chama_pts = [
            (cx - 8,  cy + hh - 2),
            (cx,      cy + hh + chama_h),
            (cx + 8,  cy + hh - 2),
        ]
        if com_buff or tier > 0:
            cor_chama = (int(255), int(200 + pulso * 55), int(pulso * 30))
        else:
            cor_chama = (int(255), int(100 + pulso * 130), int(pulso * 50))
        pygame.draw.polygon(superficie, cor_chama, chama_pts)

        # Aura dourada ao redor da nave (buff permanente ou temporário)
        if com_buff or tier > 0:
            aura_raio = int(hw + 8 + pulso * 4)
            aura_surf = pygame.Surface((aura_raio * 2, aura_raio * 2), pygame.SRCALPHA)
            aura_alpha = int(60 + pulso * 60)
            cor_aura = (255, 215, 0, aura_alpha) if tier > 0 else (100, 200, 255, aura_alpha)
            pygame.draw.circle(aura_surf, cor_aura, (aura_raio, aura_raio), aura_raio)
            superficie.blit(aura_surf, (cx - aura_raio, cy - aura_raio))

        # Corpo da nave
        cor_nave = DOURADO if (tier > 0) else CIANO
        corpo_pts = [
            (cx,        cy - hh),
            (cx - hw,   cy + hh),
            (cx + hw,   cy + hh),
        ]
        pygame.draw.polygon(superficie, cor_nave, corpo_pts)

        # Asas
        cor_asa = (200, 160, 0) if tier > 0 else (0, 180, 220)
        asa_esq = [
            (cx - hw,       cy + hh),
            (cx - hw - 12,  cy + hh - 4),
            (cx - hw + 8,   cy),
        ]
        asa_dir = [
            (cx + hw,       cy + hh),
            (cx + hw + 12,  cy + hh - 4),
            (cx + hw - 8,   cy),
        ]
        pygame.draw.polygon(superficie, cor_asa, asa_esq)
        pygame.draw.polygon(superficie, cor_asa, asa_dir)

        # Cockpit
        pygame.draw.circle(superficie, BRANCO, (cx, cy - 4), 6)
        pygame.draw.circle(superficie, (0, 120, 180), (cx, cy - 4), 4)

        # Indicador de tier na nave (pequenas estrelas acima)
        for i in range(min(tier, 5)):
            sx = cx - (min(tier, 5) - 1) * 8 + i * 16
            desenhar_estrela_simbolo(superficie, sx, cy - hh - 10, 5, DOURADO)

        # Contorno
        pygame.draw.polygon(superficie, BRANCO, corpo_pts, 1)


# ─────────────────────────────────────────────
#  CLASSE: PROJÉTIL
# ─────────────────────────────────────────────
class Projetil:
    def __init__(self, x, y, vx=0, vy=-PROJ_VELOCIDADE):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.largura = PROJ_LARGURA
        self.altura = PROJ_ALTURA
        self.brilho_anim = 0
        self.diagonal = (vx != 0)  # projétil diagonal?

    @property
    def rect(self):
        return pygame.Rect(
            int(self.x) - self.largura // 2,
            int(self.y) - self.altura,
            self.largura,
            self.altura
        )

    def atualizar(self):
        self.x += self.vx
        self.y += self.vy
        self.brilho_anim += 10

    def fora_da_tela(self):
        return (self.y + self.altura < 0 or
                self.x < -20 or self.x > LARGURA + 20)

    def desenhar(self, superficie):
        brilho_alpha = int(80 + abs(math.sin(math.radians(self.brilho_anim))) * 80)
        cor = (180, 80, 255) if self.diagonal else AMARELO
        cor_brilho = (180, 80, 255, brilho_alpha) if self.diagonal else (255, 230, 50, brilho_alpha)

        # Núcleo
        pygame.draw.rect(
            superficie, cor,
            (int(self.x) - self.largura // 2, int(self.y) - self.altura,
             self.largura, self.altura),
            border_radius=2
        )
        # Brilho
        brilho = pygame.Surface((self.largura + 4, self.altura + 4), pygame.SRCALPHA)
        brilho.fill(cor_brilho)
        superficie.blit(brilho, (int(self.x) - self.largura // 2 - 2, int(self.y) - self.altura - 2))


# ─────────────────────────────────────────────
#  CLASSE: ASTEROIDE
# ─────────────────────────────────────────────
class Asteroide:
    TAMANHOS = {
        'grande': (32, 40),
        'medio':  (22, 28),
    }

    def __init__(self, velocidade, is_buff=False):
        tamanho_key = random.choice(list(self.TAMANHOS.keys()))
        self.raio = random.randint(*self.TAMANHOS[tamanho_key])
        self.x = random.randint(self.raio, LARGURA - self.raio)
        self.y = -self.raio
        self.velocidade = velocidade
        self.rotacao = 0
        self.vel_rotacao = random.uniform(-2.5, 2.5)
        self.is_buff = is_buff
        self.brilho_anim = 0

        if is_buff:
            self.cor = (80, 60, 30)   # tom escuro para contraste com dourado
        else:
            self.cor = random.choice([CINZA, CINZA_ESCURO, (130, 110, 90)])

        self.pontos = self._gerar_forma()

    def _gerar_forma(self):
        num_pts = random.randint(7, 11)
        pontos = []
        for i in range(num_pts):
            angulo = (360 / num_pts) * i
            variacao = random.uniform(0.55, 1.0)
            r = self.raio * variacao
            rad = math.radians(angulo)
            pontos.append((r * math.cos(rad), r * math.sin(rad)))
        return pontos

    @property
    def rect(self):
        return pygame.Rect(
            self.x - self.raio,
            self.y - self.raio,
            self.raio * 2,
            self.raio * 2
        )

    def atualizar(self):
        self.y += self.velocidade
        self.rotacao += self.vel_rotacao
        self.brilho_anim += 3

    def saiu_da_tela(self):
        return self.y - self.raio > ALTURA

    def desenhar(self, superficie):
        rad = math.radians(self.rotacao)
        cos_r, sin_r = math.cos(rad), math.sin(rad)

        pts_rotacionados = []
        for px, py in self.pontos:
            rx = px * cos_r - py * sin_r + self.x
            ry = px * sin_r + py * cos_r + self.y
            pts_rotacionados.append((int(rx), int(ry)))

        pts_sombra = []
        fator = 0.75
        for px, py in self.pontos:
            rx = px * cos_r * fator - py * sin_r * fator + self.x + 2
            ry = px * sin_r * fator + py * cos_r * fator + self.y + 2
            pts_sombra.append((int(rx), int(ry)))

        pygame.draw.polygon(superficie, (40, 35, 30), pts_sombra)
        pygame.draw.polygon(superficie, self.cor, pts_rotacionados)

        if self.is_buff:
            # Contorno dourado pulsante
            pulso = abs(math.sin(math.radians(self.brilho_anim)))
            alpha_borda = int(160 + pulso * 95)
            cor_borda = (255, int(180 + pulso * 75), 0)
            pygame.draw.polygon(superficie, cor_borda, pts_rotacionados, 2)

            # Símbolo ★ no centro
            estrela_raio = max(8, self.raio // 2 - 2)
            cor_estrela = (255, int(210 + pulso * 45), int(pulso * 50))
            desenhar_estrela_simbolo(
                superficie, int(self.x), int(self.y),
                estrela_raio, cor_estrela
            )
        else:
            pygame.draw.polygon(superficie, BRANCO, pts_rotacionados, 1)


# ─────────────────────────────────────────────
#  CLASSE: PARTÍCULA (efeito de explosão)
# ─────────────────────────────────────────────
class Particula:
    def __init__(self, x, y, cor):
        angulo = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.5, 5.0)
        self.x = x
        self.y = y
        self.vx = math.cos(angulo) * speed
        self.vy = math.sin(angulo) * speed
        self.vida = random.randint(20, 45)
        self.vida_max = self.vida
        self.raio = random.randint(2, 5)
        self.cor = cor

    def atualizar(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.vida -= 1

    def vivo(self):
        return self.vida > 0

    def desenhar(self, superficie):
        alpha = int(255 * (self.vida / self.vida_max))
        raio = max(1, int(self.raio * (self.vida / self.vida_max)))
        surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.cor, alpha), (raio, raio), raio)
        superficie.blit(surf, (int(self.x) - raio, int(self.y) - raio))


# ─────────────────────────────────────────────
#  CLASSE: JOGO
# ─────────────────────────────────────────────
class Jogo:
    def __init__(self, tela, clock):
        self.tela = tela
        self.clock = clock
        self.fonte_hud  = pygame.font.SysFont("monospace", 22, bold=True)
        self.fonte_big  = pygame.font.SysFont("monospace", 64, bold=True)
        self.fonte_med  = pygame.font.SysFont("monospace", 30, bold=True)
        self.fonte_sub  = pygame.font.SysFont("monospace", 18)
        self.fonte_hud2 = pygame.font.SysFont("monospace", 18, bold=True)
        self.estrelas   = gerar_estrelas()
        self.reiniciar()

    def reiniciar(self):
        self.nave          = Nave()
        self.projeteis     = []
        self.asteroides    = []
        self.particulas    = []
        self.pontuacao     = 0
        self.game_over     = False
        self.ultimo_spawn  = pygame.time.get_ticks()
        self.tempo_inicio  = pygame.time.get_ticks()

        # ── Estado do buff ──
        self.buff_tier          = 0        # tier permanente atual
        self.buff_contador      = 0        # 0..4 → chega em 5 = tier+1
        self.buff_temp_ativo    = False    # buff temporário ligado?
        self.buff_temp_ms       = 0        # ms restantes do buff temporário
        self.buff_notif_ms      = 0        # ms para exibir notificação de tier

        # Botão "Jogar Novamente"
        bw, bh = 260, 52
        self.btn_rect = pygame.Rect(
            LARGURA // 2 - bw // 2,
            ALTURA // 2 + 70,
            bw, bh
        )
        self.btn_hover = False

    # ── Propriedades de buff ──────────────────
    @property
    def buff_ativo(self):
        """True se buff temporário OU tier permanente ≥ 1."""
        return self.buff_temp_ativo or self.buff_tier >= 1

    @property
    def velocidade_nave(self):
        bonus = BUFF_VEL_BONUS if self.buff_temp_ativo else 0
        return NAVE_VELOCIDADE + self.buff_tier * 2 + bonus

    # ── Ativar buff temporário ────────────────
    def _ativar_buff_temp(self):
        if self.buff_temp_ativo:
            self.buff_temp_ms += BUFF_DURACAO_MS   # soma o tempo
        else:
            self.buff_temp_ativo = True
            self.buff_temp_ms = BUFF_DURACAO_MS

    # ── Registrar acerto de buff ──────────────
    def _registrar_acerto_buff(self):
        self.buff_contador += 1
        if self.buff_contador >= BUFF_ACERTOS_PERMANENTE:
            self.buff_tier += 1
            self.buff_contador = 0
            self.buff_notif_ms = 3000   # exibe notificação por 3s

    # ── Spawn de asteroide ────────────────────
    def _tentar_spawn(self):
        agora = pygame.time.get_ticks()
        intervalo = calcular_intervalo_spawn(self.pontuacao, self.buff_tier)
        if agora - self.ultimo_spawn >= intervalo:
            vel = calcular_velocidade_asteroide(self.pontuacao, self.buff_tier)
            is_buff = random.random() < BUFF_CHANCE_SPAWN
            self.asteroides.append(Asteroide(vel, is_buff=is_buff))
            self.ultimo_spawn = agora

    # ── Explosão ─────────────────────────────
    def _explodir(self, x, y, cor_asteroide, is_buff=False):
        if is_buff:
            cores = [DOURADO, AMARELO, LARANJA, BRANCO, (255, 255, 150)]
            n = 35
        else:
            cores = [LARANJA, AMARELO, VERMELHO, BRANCO, cor_asteroide]
            n = 20
        for _ in range(n):
            self.particulas.append(Particula(x, y, random.choice(cores)))

    # ── Atualizar ────────────────────────────
    def atualizar(self, teclas, dt_ms):
        if self.game_over:
            return

        # Atualizar timer do buff temporário
        if self.buff_temp_ativo:
            self.buff_temp_ms -= dt_ms
            if self.buff_temp_ms <= 0:
                self.buff_temp_ativo = False
                self.buff_temp_ms = 0

        # Atualizar notificação de tier
        if self.buff_notif_ms > 0:
            self.buff_notif_ms -= dt_ms

        # Nave
        self.nave.mover(teclas, self.velocidade_nave)

        # Disparo automático (ao segurar ESPAÇO)
        if teclas[pygame.K_SPACE]:
            if self.nave.pode_atirar():
                novos = self.nave.atirar(com_buff=self.buff_ativo)
                self.projeteis.extend(novos)

        # Projéteis
        for p in self.projeteis[:]:
            p.atualizar()
            if p.fora_da_tela():
                self.projeteis.remove(p)

        # Spawn asteroide
        self._tentar_spawn()

        # Asteroides
        for a in self.asteroides[:]:
            a.atualizar()

            if a.saiu_da_tela():
                self.game_over = True
                return

            if self.nave.rect.colliderect(a.rect):
                self._explodir(self.nave.x, self.nave.y, CIANO)
                self.game_over = True
                return

            for p in self.projeteis[:]:
                if p.rect.colliderect(a.rect):
                    self._explodir(int(a.x), int(a.y), a.cor, is_buff=a.is_buff)
                    if a.is_buff:
                        self._ativar_buff_temp()
                        self._registrar_acerto_buff()
                    self.asteroides.remove(a)
                    self.projeteis.remove(p)
                    self.pontuacao += PONTOS_POR_ACERTO
                    break

        # Partículas
        for pt in self.particulas[:]:
            pt.atualizar()
            if not pt.vivo():
                self.particulas.remove(pt)

    # ── Desenhar fundo ───────────────────────
    def _desenhar_fundo(self):
        self.tela.fill(PRETO)
        for x in range(0, LARGURA, 80):
            pygame.draw.line(self.tela, (10, 10, 20), (x, 0), (x, ALTURA))
        for y in range(0, ALTURA, 80):
            pygame.draw.line(self.tela, (10, 10, 20), (0, y), (LARGURA, y))
        for ex, ey, tam in self.estrelas:
            brilho = random.randint(180, 255)
            cor = (brilho, brilho, brilho)
            if tam == 1:
                self.tela.set_at((ex, ey), cor)
            else:
                pygame.draw.circle(self.tela, cor, (ex, ey), tam - 1)

    # ── HUD ──────────────────────────────────
    def _desenhar_hud(self):
        # Pontuação
        texto = self.fonte_hud.render(f"PONTOS: {self.pontuacao:05d}", True, VERDE)
        self.tela.blit(texto, (14, 12))

        # Nível de dificuldade por pontuação
        nivel = self.pontuacao // 50 + 1
        txt_nivel = self.fonte_hud.render(f"NÍVEL: {nivel}", True, CIANO)
        self.tela.blit(txt_nivel, (14, 36))

        # Tier permanente
        if self.buff_tier > 0:
            txt_tier = self.fonte_hud2.render(f"TIER BUFF: {self.buff_tier}", True, DOURADO)
            self.tela.blit(txt_tier, (14, 60))

        # Contador de buffs → próximo tier
        estrelas_str = "★" * self.buff_contador + "☆" * (BUFF_ACERTOS_PERMANENTE - self.buff_contador)
        cor_contador = DOURADO if self.buff_temp_ativo else (160, 130, 50)
        txt_cnt = self.fonte_hud2.render(estrelas_str, True, cor_contador)
        self.tela.blit(txt_cnt, (14, 80 if self.buff_tier > 0 else 60))

        # Barra de buff temporário
        if self.buff_temp_ativo:
            barra_x, barra_y = 14, 102 if self.buff_tier > 0 else 82
            barra_larg = 200
            barra_alt = 10
            proporcao = self.buff_temp_ms / BUFF_DURACAO_MS
            proporcao = min(proporcao, 1.0)

            # Fundo
            pygame.draw.rect(self.tela, (50, 40, 10),
                             (barra_x, barra_y, barra_larg, barra_alt), border_radius=4)
            # Preenchimento
            pygame.draw.rect(self.tela, DOURADO,
                             (barra_x, barra_y, int(barra_larg * proporcao), barra_alt),
                             border_radius=4)
            # Borda
            pygame.draw.rect(self.tela, (200, 160, 0),
                             (barra_x, barra_y, barra_larg, barra_alt), 1, border_radius=4)

            seg_restante = self.buff_temp_ms / 1000
            txt_timer = self.fonte_hud2.render(f"BUFF {seg_restante:.1f}s", True, AMARELO)
            self.tela.blit(txt_timer, (barra_x + barra_larg + 8, barra_y - 2))

        # Notificação de tier ganho
        if self.buff_notif_ms > 0:
            alpha = min(255, int(self.buff_notif_ms / 3000 * 255 * 3))
            alpha = min(alpha, 255)
            notif = self.fonte_med.render(f"★ TIER {self.buff_tier} BUFF PERMANENTE! ★", True, DOURADO)
            notif.set_alpha(alpha)
            self.tela.blit(notif, notif.get_rect(center=(LARGURA // 2, ALTURA // 2 - 150)))

        # Linha separadora
        pygame.draw.line(self.tela, (30, 30, 50), (0, 120), (LARGURA, 120), 1)

    # ── Tela de Game Over ────────────────────
    def _desenhar_game_over(self, mouse_pos):
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.tela.blit(overlay, (0, 0))

        txt_go = self.fonte_big.render("GAME OVER", True, VERMELHO)
        rect_go = txt_go.get_rect(center=(LARGURA // 2, ALTURA // 2 - 90))
        sombra = self.fonte_big.render("GAME OVER", True, (80, 0, 0))
        self.tela.blit(sombra, rect_go.move(3, 3))
        self.tela.blit(txt_go, rect_go)

        txt_pts = self.fonte_med.render(f"Pontuação Final: {self.pontuacao}", True, AMARELO)
        self.tela.blit(txt_pts, txt_pts.get_rect(center=(LARGURA // 2, ALTURA // 2 - 20)))

        if self.buff_tier > 0:
            txt_tier = self.fonte_hud2.render(
                f"Tier de Buff Atingido: {self.buff_tier} ({'★' * min(self.buff_tier, 5)})",
                True, DOURADO
            )
            self.tela.blit(txt_tier, txt_tier.get_rect(center=(LARGURA // 2, ALTURA // 2 + 15)))

        # Botão
        self.btn_hover = self.btn_rect.collidepoint(mouse_pos)
        cor_btn   = (50, 200, 100) if self.btn_hover else (30, 140, 70)
        cor_borda = (150, 255, 180) if self.btn_hover else (80, 200, 120)
        escala    = 1.04 if self.btn_hover else 1.0

        bw = int(self.btn_rect.width  * escala)
        bh = int(self.btn_rect.height * escala)
        bx = self.btn_rect.centerx - bw // 2
        by = self.btn_rect.centery - bh // 2
        btn_r = pygame.Rect(bx, by, bw, bh)

        pygame.draw.rect(self.tela, cor_btn,   btn_r, border_radius=10)
        pygame.draw.rect(self.tela, cor_borda, btn_r, 2, border_radius=10)

        txt_btn = self.fonte_med.render("▶  Jogar Novamente", True, BRANCO)
        self.tela.blit(txt_btn, txt_btn.get_rect(center=btn_r.center))

        txt_hint = self.fonte_sub.render("ou pressione R para reiniciar", True, (120, 120, 140))
        self.tela.blit(txt_hint, txt_hint.get_rect(center=(LARGURA // 2, self.btn_rect.bottom + 22)))

    # ── Desenhar ─────────────────────────────
    def desenhar(self, mouse_pos):
        self._desenhar_fundo()

        for a in self.asteroides:
            a.desenhar(self.tela)

        if not self.game_over:
            self.nave.desenhar(self.tela,
                               com_buff=self.buff_temp_ativo,
                               tier=self.buff_tier)

        for p in self.projeteis:
            p.desenhar(self.tela)

        for pt in self.particulas:
            pt.desenhar(self.tela)

        self._desenhar_hud()

        if self.game_over:
            self._desenhar_game_over(mouse_pos)

    # ── Tratar clique no botão ───────────────
    def tratar_clique(self, pos):
        if self.game_over and self.btn_rect.collidepoint(pos):
            self.reiniciar()


# ─────────────────────────────────────────────
#  LOOP PRINCIPAL
# ─────────────────────────────────────────────
def main():
    pygame.init()
    pygame.font.init()
    tela = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption(TITULO)
    clock = pygame.time.Clock()

    jogo = Jogo(tela, clock)

    while True:
        dt_ms = clock.tick(FPS)
        eventos = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        for evento in eventos:
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                jogo.tratar_clique(evento.pos)

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_r and jogo.game_over:
                    jogo.reiniciar()

        teclas = pygame.key.get_pressed()
        jogo.atualizar(teclas, dt_ms)
        jogo.desenhar(mouse_pos)

        pygame.display.flip()


if __name__ == "__main__":
    main()
