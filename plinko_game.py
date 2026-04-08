import pygame
import random
import math
import sys

# --- Configuration & Constants ---
WIDTH, HEIGHT = 1200, 800
SIDEBAR_W = 320
TOPBAR_H = 60
FPS = 60

# --- Exact Colors from Reference Image ---
C_HEADER = (33, 37, 46)
C_SIDEBAR = (43, 48, 58)
C_MAIN = (23, 26, 33)

C_TEXT_MUTE = (177, 182, 198)
C_TEXT_WHITE = (255, 255, 255)
C_TEXT_BLACK = (10, 10, 10)

C_BTN_GREEN = (40, 201, 102)
C_BTN_GREEN_HOVER = (60, 221, 122)
C_BTN_BLUE = (59, 105, 255)
C_INPUT_BG = (26, 29, 36)
C_INPUT_BTN = (60, 66, 78)

C_PEG = (255, 255, 255)
C_BALL = (255, 255, 255)

# Stake-Style Multipliers
MULTIPLIERS = {
    8: {
        "Low": [5.6, 2.1, 1.1, 1.0, 0.5, 1.0, 1.1, 2.1, 5.6],
        "Medium": [13, 3, 1.3, 0.7, 0.4, 0.7, 1.3, 3, 13],
        "High": [29, 4, 1.5, 0.3, 0.2, 0.3, 1.5, 4, 29]
    },
    12: {
        "Low": [10, 3, 1.6, 1.4, 1.1, 1, 0.5, 1, 1.1, 1.4, 1.6, 3, 10],
        "Medium": [33, 11, 4, 2, 1.1, 0.6, 0.3, 0.6, 1.1, 2, 4, 11, 33],
        "High": [170, 24, 8.1, 2, 0.7, 0.2, 0.2, 0.2, 0.7, 2, 8.1, 24, 170]
    },
    16: {
        "Low": [16, 9, 2, 1.4, 1.4, 1.2, 1.1, 1, 0.5, 1, 1.1, 1.2, 1.4, 1.4, 2, 9, 16],
        "Medium": [110, 41, 10, 5, 3, 1.5, 1, 0.5, 0.3, 0.5, 1, 1.5, 3, 5, 10, 41, 110],
        "High": [1000, 130, 26, 9, 4, 2, 0.2, 0.2, 0.2, 0.2, 0.2, 2, 4, 9, 26, 130, 1000]
    }
}

def get_slot_color(mult):
    """Returns exact gradient colors matching the screenshot."""
    if mult >= 100: return (255, 0, 63)
    if mult >= 40: return (255, 31, 58)
    if mult >= 10: return (255, 58, 51)
    if mult >= 5: return (255, 95, 42)
    if mult >= 3: return (255, 127, 33)
    if mult >= 1.5: return (255, 159, 24)
    if mult >= 1: return (255, 191, 15)
    if mult >= 0.5: return (255, 223, 6)
    return (255, 255, 0)

# --- Classes ---

class Board:
    def __init__(self):
        self.rows = 16
        self.risk = "Medium"
        self.center_x = SIDEBAR_W + (WIDTH - SIDEBAR_W) / 2
        self.top_y = TOPBAR_H + 80
        self.board_height = HEIGHT - self.top_y - 80

    def get_multipliers(self):
        return MULTIPLIERS[self.rows][self.risk]

    def get_peg_pos(self, r, c):
        """Calculates exact peg position. Matches the 3-peg top row geometry."""
        spacing_x = 36 if self.rows == 16 else (42 if self.rows == 12 else 50)
        spacing_y = self.board_height / (self.rows + 1)
        
        # Row r has (r + 3) pegs.
        row_width = (r + 2) * spacing_x
        start_x = self.center_x - row_width / 2
        return start_x + c * spacing_x, self.top_y + r * spacing_y

    def get_slot_pos(self, c):
        """Calculates slot X, Y coordinates."""
        spacing_x = 36 if self.rows == 16 else (42 if self.rows == 12 else 50)
        spacing_y = self.board_height / (self.rows + 1)
        row_width = (self.rows + 1) * spacing_x
        start_x = self.center_x - row_width / 2
        return start_x + c * spacing_x, self.top_y + self.rows * spacing_y

    def get_target_slot(self):
        """Backend custom probability distribution generator."""
        weights = []
        for k in range(self.rows + 1):
            p = math.comb(self.rows, k) / (2 ** self.rows)
            if self.risk == "Low": w = p ** 1.5
            elif self.risk == "High": w = p ** 0.5
            else: w = p
            weights.append(w)
        return random.choices(range(self.rows + 1), weights=weights, k=1)[0]

class Ball:
    def __init__(self, board, final_slot, bet_amount):
        self.board = board
        self.bet_amount = bet_amount
        self.r = 0
        self.c = 1 # Drops cleanly into the middle gap of the 3-peg top row
        
        # Determine randomized path enforcing terminal slot
        self.path = ['R'] * final_slot + ['L'] * (board.rows - final_slot)
        random.shuffle(self.path)
        
        self.progress = 0.0
        self.speed = 0.06
        self.x, self.y = self.board.get_peg_pos(self.r, self.c)
        self.dead = False
        self.winnings = 0

    def update(self):
        if self.dead: return True

        self.progress += self.speed
        if self.progress >= 1.0:
            self.progress = 0.0
            if self.path:
                move = self.path.pop(0)
                self.r += 1
                if move == 'R': self.c += 1
            else:
                self.dead = True
                mult = self.board.get_multipliers()[self.c - 1] # Offset logic for slots
                self.winnings = self.bet_amount * mult
                return True

        # Interpolate movement
        start_x, start_y = self.board.get_peg_pos(self.r, self.c)
        if self.path:
            end_r = self.r + 1
            end_c = self.c + (1 if self.path[0] == 'R' else 0)
            end_x, end_y = self.board.get_peg_pos(end_r, end_c)
        else:
            end_x, end_y = self.board.get_slot_pos(self.c - 0.5)

        self.x = start_x + (end_x - start_x) * self.progress
        self.y = start_y + (end_y - start_y) * self.progress

        # Realistic bounce arc
        arc_height = 25
        self.y -= math.sin(self.progress * math.pi) * arc_height
        return False

    def draw(self, surface):
        pygame.draw.circle(surface, C_BALL, (int(self.x), int(self.y)), 8)

class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.alpha = 255
        self.font = pygame.font.SysFont("Segoe UI, Arial", 16, bold=True)

    def update(self):
        self.y -= 1.5
        self.alpha -= 4
        return self.alpha <= 0

    def draw(self, surface):
        txt_surf = self.font.render(self.text, True, self.color)
        txt_surf.set_alpha(max(0, self.alpha))
        surface.blit(txt_surf, txt_surf.get_rect(center=(self.x, self.y)))


class PlinkoGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Plinko Replica")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.f_logo = pygame.font.SysFont("Segoe UI, Arial", 26, bold=True, italic=True)
        self.f_normal = pygame.font.SysFont("Segoe UI, Arial", 14)
        self.f_bold = pygame.font.SysFont("Segoe UI, Arial", 14, bold=True)
        self.f_btn = pygame.font.SysFont("Segoe UI, Arial", 16, bold=True)
        self.f_mult = pygame.font.SysFont("Segoe UI, Arial", 11, bold=True)

        self.board = Board()
        self.balls = []
        self.floating_texts = []
        self.balance = 200.00
        self.bet = 1.00

        # UI Rects
        self.r_half = pygame.Rect(SIDEBAR_W - 100, 185, 30, 38)
        self.r_double = pygame.Rect(SIDEBAR_W - 70, 185, 30, 38)
        self.r_risk = pygame.Rect(20, 275, SIDEBAR_W - 40, 40)
        self.r_rows = pygame.Rect(20, 355, SIDEBAR_W - 40, 40)
        self.r_drop = pygame.Rect(20, 430, SIDEBAR_W - 40, 50)
        self.r_add = pygame.Rect(WIDTH/2 + 60, 10, 60, 40)

    def handle_events(self):
        pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.r_half.collidepoint(pos):
                    self.bet = max(0.5, self.bet / 2)
                elif self.r_double.collidepoint(pos):
                    self.bet = min(self.balance, self.bet * 2)
                elif self.r_add.collidepoint(pos):
                    self.balance += 100.00
                    
                elif self.r_risk.collidepoint(pos) and not self.balls:
                    risks = ["Low", "Medium", "High"]
                    self.board.risk = risks[(risks.index(self.board.risk) + 1) % 3]
                elif self.r_rows.collidepoint(pos) and not self.balls:
                    rows = [8, 12, 16]
                    self.board.rows = rows[(rows.index(self.board.rows) + 1) % 3]
                    
                elif self.r_drop.collidepoint(pos) and self.balance >= self.bet:
                    self.balance -= self.bet
                    self.balls.append(Ball(self.board, self.board.get_target_slot(), self.bet))

    def draw_topbar(self):
        pygame.draw.rect(self.screen, C_HEADER, (0, 0, WIDTH, TOPBAR_H))
        
        # Logo
        logo = self.f_logo.render("Plinko", True, C_TEXT_WHITE)
        self.screen.blit(logo, (20, 12))
        
        # Balance Box
        bx = WIDTH / 2 - 60
        pygame.draw.rect(self.screen, C_INPUT_BG, (bx, 10, 120, 40), border_radius=5)
        bal_str = f"$ {self.balance:.2f}"
        self.screen.blit(self.f_bold.render(bal_str, True, C_TEXT_WHITE), (bx + 15, 20))
        
        # Add Button
        pygame.draw.rect(self.screen, C_BTN_BLUE, self.r_add, border_radius=5)
        add_lbl = self.f_btn.render("Add", True, C_TEXT_WHITE)
        self.screen.blit(add_lbl, add_lbl.get_rect(center=self.r_add.center))

    def draw_sidebar(self):
        pygame.draw.rect(self.screen, C_SIDEBAR, (0, TOPBAR_H, SIDEBAR_W, HEIGHT - TOPBAR_H))
        
        # Manual / Auto Tabs
        pygame.draw.rect(self.screen, C_INPUT_BG, (20, 80, SIDEBAR_W - 40, 44), border_radius=22)
        pygame.draw.rect(self.screen, C_INPUT_BTN, (24, 84, (SIDEBAR_W-48)//2, 36), border_radius=18)
        self.screen.blit(self.f_bold.render("Manual", True, C_TEXT_WHITE), (65, 93))
        self.screen.blit(self.f_bold.render("Auto", True, C_TEXT_MUTE), (220, 93))
        
        # Bet Input
        self.screen.blit(self.f_normal.render("Bet Amount", True, C_TEXT_MUTE), (20, 160))
        pygame.draw.rect(self.screen, C_INPUT_BG, (20, 185, SIDEBAR_W - 40, 38), border_radius=4)
        self.screen.blit(self.f_bold.render(f"$ {self.bet:.2f}", True, C_TEXT_WHITE), (30, 195))
        
        # 1/2 and 2x buttons
        pygame.draw.rect(self.screen, C_INPUT_BTN, self.r_half)
        pygame.draw.rect(self.screen, C_INPUT_BTN, self.r_double, border_top_right_radius=4, border_bottom_right_radius=4)
        pygame.draw.line(self.screen, C_SIDEBAR, (SIDEBAR_W - 70, 185), (SIDEBAR_W - 70, 223), 2)
        
        self.screen.blit(self.f_bold.render("½", True, C_TEXT_WHITE), (self.r_half.x + 8, self.r_half.y + 8))
        self.screen.blit(self.f_bold.render("2×", True, C_TEXT_WHITE), (self.r_double.x + 6, self.r_double.y + 8))

        # Risk Dropdown
        self.screen.blit(self.f_normal.render("Risk", True, C_TEXT_MUTE), (20, 250))
        pygame.draw.rect(self.screen, C_INPUT_BG, self.r_risk, border_radius=4)
        self.screen.blit(self.f_bold.render(self.board.risk, True, C_TEXT_WHITE), (30, 285))
        self.screen.blit(self.f_bold.render("v", True, C_TEXT_MUTE), (self.r_risk.right - 20, 285))

        # Rows Dropdown
        self.screen.blit(self.f_normal.render("Rows", True, C_TEXT_MUTE), (20, 330))
        pygame.draw.rect(self.screen, C_INPUT_BG, self.r_rows, border_radius=4)
        self.screen.blit(self.f_bold.render(str(self.board.rows), True, C_TEXT_WHITE), (30, 365))
        self.screen.blit(self.f_bold.render("v", True, C_TEXT_MUTE), (self.r_rows.right - 20, 365))

        # Drop Button
        hover = self.r_drop.collidepoint(pygame.mouse.get_pos())
        color = C_BTN_GREEN_HOVER if hover else C_BTN_GREEN
        pygame.draw.rect(self.screen, color, self.r_drop, border_radius=5)
        drop_lbl = self.f_btn.render("Drop Ball", True, C_TEXT_BLACK)
        self.screen.blit(drop_lbl, drop_lbl.get_rect(center=self.r_drop.center))

    def draw_board(self):
        # Draw Main Background
        pygame.draw.rect(self.screen, C_MAIN, (SIDEBAR_W, TOPBAR_H, WIDTH - SIDEBAR_W, HEIGHT - TOPBAR_H))

        # Draw Pegs
        for r in range(self.board.rows):
            for c in range(r + 3):
                x, y = self.board.get_peg_pos(r, c)
                pygame.draw.circle(self.screen, C_PEG, (int(x), int(y)), 4)

        # Draw Multiplier Slots
        mults = self.board.get_multipliers()
        spacing_x = 36 if self.board.rows == 16 else (42 if self.board.rows == 12 else 50)
        
        for c, mult in enumerate(mults):
            x, y = self.board.get_slot_pos(c + 0.5)
            color = get_slot_color(mult)
            
            rect = pygame.Rect(0, 0, spacing_x - 4, 26)
            rect.center = (x, y + 15)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            
            txt = f"{mult}x" if mult < 100 else f"{mult}"
            txt_surf = self.f_mult.render(txt, True, C_TEXT_BLACK)
            self.screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

    def run(self):
        while True:
            self.handle_events()

            self.draw_board()
            self.draw_sidebar()
            self.draw_topbar()

            # Update & Draw Balls
            for ball in self.balls[:]:
                if ball.update():
                    self.balance += ball.winnings
                    slot_x, slot_y = self.board.get_slot_pos(ball.c - 0.5)
                    color = C_BTN_GREEN if ball.winnings >= ball.bet_amount else C_TEXT_MUTE
                    self.floating_texts.append(FloatingText(slot_x, slot_y - 20, f"+${ball.winnings:.2f}", color))
                    self.balls.remove(ball)
                else:
                    ball.draw(self.screen)

            # Update & Draw Floating Text
            for txt in self.floating_texts[:]:
                if txt.update():
                    self.floating_texts.remove(txt)
                else:
                    txt.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = PlinkoGame()
    game.run()