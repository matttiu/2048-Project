# --- 2048 v1.0 – by Matttiu ---
# Stable release: optimized animations, merge logic, and UI
# Built with: Python 3 & Tkinter
# Credits: Threes / 2048 concept inspired by Gabriele Cirulli

# --- Importing Libraries for 2048 Game --- 
from tkinter import * 
import random 
import os
import json 
import time 

# --- Creating Animation Class --- 
class AnimationManager: 
    def __init__(self, master, fps=60):
        self.master = master 
        self.fps = fps 
        self._tick_delay = max(1, int(1000 / fps)) 
        self.animations = [] 
        self.running = False 

    def add_animation(self, func, duration=200, steps=10, on_complete=None): 

        anim = {
            "func": func, 
            "duration": max(1, int(duration)), 
            "start": time.time(), 
            "on_complete": on_complete
        }
        self.animations.append(anim) 
        if not self.running: 
            self.running = True 
            self.master.after(0, self._tick) 

    def _tick(self): 
        now = time.time() 
        still_active = [] 

        for anim in self.animations: 
            elapsed_ms = (now - anim["start"]) * 1000.0
            progress = min(elapsed_ms / anim["duration"], 1.0)
            try: 
                anim["func"](progress) 
            except Exception as e: 
                print("Animation func error:", e) 
            if progress < 1.0: 
                still_active.append(anim)
            else: 
                if anim["on_complete"]: 
                    try:
                        anim["on_complete"]()
                    except Exception as e: 
                        print("Animation on_complete error:", e)

        self.animations = still_active 
        if self.animations: 
            self.master.after(self._tick_delay, self._tick)
        else: 
            self.running = False

# --- Creating Main Class ---
class play_2048 (Tk): 

    game_board = [] 
    new_random_tiles = [2, 2, 2, 2, 2, 2, 4]
    score = 0 
    high_score = 0 
    game_score = 0 
    highest_score = 0 
    CELL_SIZE = 100 
    CELL_PADDING = 10

    def __init__(self, *args, **kwargs): 
        Tk.__init__(self, *args, **kwargs) 

        self.last_spawned_tile = None  

        self.game_score = StringVar(self)
        self.game_score.set("0")
        self.highest_score = StringVar(self)
        self.highest_score.set("0")

        self.score = 0
        self.high_score = 0
        self.game_board = [[0]*4 for _ in range(4)]

        self.button_frame = Frame(self)
        self.button_frame.pack(side="top", fill="x", pady=5)

        Button(self.button_frame, text="New Game", font=("times new roman", 15), command=self.new_game).pack(side="left", padx=4)
        Label(self.button_frame, text="Score:", font=("times new roman", 15)).pack(side="left", padx=4)
        Label(self.button_frame, textvariable=self.game_score, font=("times new roman", 15)).pack(side="left", padx=4)
        Label(self.button_frame, text="Record:", font=("times new roman", 15)).pack(side="left", padx=4)
        Label(self.button_frame, textvariable=self.highest_score, font=("times new roman", 15)).pack(side="left", padx=4)
 
        self.debug_frame = Frame(self.button_frame) 

        Button(self.debug_frame, text="DBG: Win", command=self.force_win).pack(side="left", padx=4)
        Button(self.debug_frame, text="DBG: Game Over", command=self.force_game_over).pack(side="left", padx=4) 

        self.debug_visible = False 

        self.bind_all("<Control-Shift-D>", self.toggle_debug_menu) 

        self.canvas = Canvas(self, width=410, height=410, borderwidth=5, highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand="false")  

        self.canvas.create_rectangle(0, 0, 410, 410, fill="#bbada0")

        self.animations = AnimationManager(self) 

        self.bind_all('<Key>', self.moves)

        if self.load_game_state():
            self.game_score.set(str(self.score))
            self.highest_score.set(str(self.high_score))
            self.show_board()  
        else:
            self.new_game()    
        
        self.protocol("WM_DELETE_WINDOW", self.on_exit)
    
    # --- Animate Tile Spawning --- 
    def animate_spawn(self, item):

        if isinstance(item, (tuple, list)): 
            rect_id, text_id = item[0], (item[1] if len(item) > 1 else None) 
        else: 
            rect_id, text_id = item, None

        bbox = self.canvas.bbox(rect_id) 
        if not bbox: 
            return 
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2)/2
        cy = (y1 + y2)/2

        duration = 200
        steps = 10
        initial_scale = 0.3
        final_scale = 1.0

        def step(progress):  
            scale = initial_scale + (final_scale - initial_scale) * progress
            new_coords = [] 
            for x, y in zip([x1, x2, x2, x1], [y1, y1, y2, y2]): 
                new_x = cx + (x - cx) * scale 
                new_y = cy + (y - cy) * scale 
                new_coords.append(new_x) 
                new_coords.append(new_y) 
            
            self.canvas.coords(rect_id, *new_coords) 

            if text_id: 
                self.canvas.coords(text_id, cx, cy)

        self.animations.add_animation(step, duration, steps)

    # --- Animate Tile Merging --- 
    def animate_merge(self, item, row=None, column=None):
        rect_id, text_id = item if isinstance(item, (tuple, list)) else (item, None)
         
        try: 
            bbox = self.canvas.bbox(rect_id)
        except Exception:
            bbox = None 
            if not bbox: 
                return

        original_coords = self.canvas.coords(rect_id)
        if not original_coords: 
            return
        xs = original_coords[::2]
        ys = original_coords[1::2]

        if row is not None and column is not None:
            cx = self.CELL_PADDING + column * (self.CELL_SIZE + self.CELL_PADDING) + self.CELL_SIZE / 2
            cy = self.CELL_PADDING + row * (self.CELL_SIZE + self.CELL_PADDING) + self.CELL_SIZE / 2
        else:
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)

        duration = 120
        pulse_scale = 0.3

        def step(progress):
            if progress < 0.5:
                scale = 1 + pulse_scale * (progress * 2)
            else:
                scale = 1 + pulse_scale * (1 - (progress - 0.5) * 2)

            new_coords = []
            for x, y in zip(xs, ys):
                new_x = cx + (x - cx) * scale
                new_y = cy + (y - cy) * scale
                new_coords.extend([new_x, new_y])
            self.canvas.coords(rect_id, *new_coords)

            bbox = self.canvas.bbox(rect_id)
            if text_id and bbox:
                x1, y1, x2, y2 = bbox
                self.canvas.coords(text_id, (x1 + x2) / 2, (y1 + y2) / 2)

            if progress >= 1.0:
                self.canvas.coords(rect_id, *original_coords)
                if text_id:
                    bbox = self.canvas.bbox(rect_id)
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        self.canvas.coords(text_id, (x1 + x2) / 2, (y1 + y2) / 2)

        self.animations.add_animation(step, duration)

    # --- Add new Tiles with 2 or 4 --- 
    def new_tiles(self): 
        index = random.randint(0, 6) 
        
        while not self.full(): 
            x = random.randint(0, 3) 
            y = random.randint(0, 3) 

            if self.game_board[x][y] == 0: 
                self.game_board[x][y] = self.new_random_tiles[index] 
                self.last_spawned_tile = (x, y) 

                self.show_board() 
                break
            
    # --- Make the tiles rounded with mathematics --- 
    def create_rounded_rectangle(self, x1, y1, x2, y2, radius=15, **kwargs):
        points =  [ 
            x1+radius, y1,
            x1+radius, y1, 
            x2-radius, y1, 
            x2-radius, y1, 
            x2, y1, 
            x2, y1+radius, 
            x2, y1+radius, 
            x2, y2-radius, 
            x2, y2-radius, 
            x2, y2, 
            x2-radius, y2, 
            x2-radius, y2, 
            x1+radius, y2, 
            x1+radius, y2, 
            x1, y2, 
            x1, y2-radius,
            x1, y2-radius, 
            x1, y1+radius, 
            x1, y1+radius, 
            x1, y1
        ]    
        return self.canvas.create_polygon(points, **kwargs, smooth=True)       

    # --- Draws the rounded tiles --- 
    def rounded_rectangle(self, x1, y1, x2, y2, r=25, color="#eee4da"):
        points = [
            x1+r, y1, 
            x2-r, y1, 
            x2, y1, x2, y1+r, 
            x2, y2-r, 
            x2, y2, x2-r, y2, 
            x1+r, y2, 
            x1, y2, x1, y2-r, 
            x1, y1+r, 
            x1, y1
        ]
        return self.canvas.create_polygon(points, smooth=True, fill=color, outline="")

    # --- Shows game board ---    
    def show_board(self):
        cellwidth = 100
        cellheight = 100 
        padding = 10
        self.square = {}  

        self.canvas.delete("board_bg") 
        self.canvas.create_rectangle(0, 0, 410, 410, fill="#bbada0", outline="", tags="board_bg")  

        self.canvas.delete("tile")

        for column in range(4): 
            for row in range(4):  
                x1 = column * cellwidth + padding
                y1 = row * cellheight + padding 
                x2 = x1 + cellwidth - padding
                y2 = y1 + cellheight - padding
                num = self.game_board[row][column]
                if num == 0 : 
                    self.show_number0(row, column, x1, y1, x2, y2) 
                else: 
                    is_new = (self.last_spawned_tile == (row, column)) 
                    self.show_number(row, column, x1, y1, x2, y2, num, is_new=is_new) 

    # --- Check if Board is Full --- 
    def full(self):
        for i in range(0, 4): 
            for j in range(0, 4): 
                if (self.game_board[i][j] == 0): 
                    return False
        return True

    # --- Shows color of grid when there are no numbers --- 
    def show_number0(self, row, column, a, b, c, d): 
        tile_id = self.create_rounded_rectangle(a, b, c, d, fill="#cdc1b4", tags=("rect", "tile")) 

        self.square[row, column] = (tile_id, None)

    # --- Shows color of grid and respective numbers --- 
    def show_number(self, row, column, a, b, c, d, num, is_new=False): 
        if is_new and num == 2:
            fill_color = "#e0f2f8" 
            text_color = "#f78a8a" 
        elif is_new and num == 4:
            fill_color = "#b8dbe5" 
            text_color = "#f78a8a"
        else: 
            bg_color = {
                '2': '#eee4da', '4': '#ede0c8', '8': '#f2b179', '16': '#f59563',
                '32': '#f67c5f', '64': '#f65e3b', '128': '#edcf72', '256': '#edcc61',
                '512': '#f2b179', '1024': '#f59563', '2048': '#edc22e'
            }
            text_color_dict = {
                '2': '#776e65', '4': '#776e65', '8': '#f9f6f2', '16': '#f9f6f2',
                '32': '#f9f6f2', '64': '#f9f6f2', '128': '#f9f6f2', '256': '#f9f6f2',
                '512': '#f9f6f2', '1024': '#f9f6f2', '2048': '#f9f6f2'
            }
            fill_color = bg_color.get(str(num), "#3c3a32")
            text_color = text_color_dict.get(str(num), "#f9f6f2") 

        shadow_id = self.canvas.create_rectangle(a+3, b+3, c+3, d+3, fill="#b3a396", outline="", tags=("tile")) 

        tile_id = self.rounded_rectangle(a, b, c, d, color=fill_color) 
        self.canvas.addtag_withtag("tile", tile_id)

        font_size = 36 if num < 1024 else 28 
        text_id = self.canvas.create_text((a + c)/2, (b + d)/2, text=str(num), fill=text_color, font=("Arial", font_size)) 
        self.canvas.addtag_withtag("tile", text_id) 

        self.canvas.tag_raise(text_id, tile_id)

        self.square[row, column] = (tile_id, text_id) 

        if is_new: 
            self.animate_spawn(self.square[row, column])  

    # --- Get Tile background color --- 
    def get_text_color(self, num): 
        if num in (2, 4): 
            return '#776e65' 
        return '#f9f6f2'
    
    # --- Helper Function for animations --- 
    def get_color(self, num):       
        bg_color = {
            2: '#eee4da', 4: '#ede0c8', 8: '#f2b179',
            16: '#f59563', 32: '#f67c5f', 64: '#f65e3b',
            128: '#edcf72', 256: '#edcc61', 512: '#f2b179',
            1024: '#f59563', 2048: '#edc22e'
        }
        return bg_color.get(num, "#3c3a32")

    # --- Accepts different events given by user --- 
    def moves(self, event):
        if getattr(self, "overlay_active", False):
            return

        direction = event.keysym
        merge_positions = []

        def process_line(line, line_index, reverse=False, is_col=False):
            new_line = []
            compact = [v for v in line if v != 0]
            j = 0
            while j < len(compact):
                if j + 1 < len(compact) and compact[j] == compact[j + 1]:
                    merged_val = compact[j] * 2
                    new_line.append(merged_val)

                    if is_col:
                        r, c = (j if not reverse else 3-j, line_index)
                    else:
                        r, c = (line_index, j if not reverse else 3-j)
                    merge_positions.append((r, c))

                    self.score += merged_val
                    j += 2
                else:
                    new_line.append(compact[j])
                    j += 1

            while len(new_line) < 4:
                new_line.append(0)

            if reverse:
                new_line = new_line[::-1]
            return new_line

        old_board = [row[:] for row in self.game_board]

        if direction == "Left":
            for i in range(4):
                self.game_board[i] = process_line(self.game_board[i], i, reverse=False, is_col=False)
        elif direction == "Right":
            for i in range(4):
                self.game_board[i] = process_line(self.game_board[i], i, reverse=True, is_col=False)
        elif direction == "Up":
            for j in range(4):
                col = [self.game_board[i][j] for i in range(4)]
                new_col = process_line(col, j, reverse=False, is_col=True)
                for i in range(4):
                    self.game_board[i][j] = new_col[i]
        elif direction == "Down":
            for j in range(4):
                col = [self.game_board[i][j] for i in range(4)]
                new_col = process_line(col, j, reverse=True, is_col=True)
                for i in range(4):
                    self.game_board[i][j] = new_col[i]

        if self.game_board != old_board:
            self.new_tiles()  
            self.show_board()  

            for r, c in merge_positions:
                if (r, c) in self.square and old_board[r][c] != 0:
                    self.animate_merge(self.square[r, c], r, c)


        self.game_score.set(str(self.score))
        if self.score > self.high_score:
            self.high_score = self.score
            self.highest_score.set(str(self.high_score))

        self.game_over()
        self.save_game_state()
    
    # --- Creates new Game for User --- 
    def new_game(self):   

        self.reset_overlay()
        self.canvas.delete("overlay")
        self.canvas.itemconfigure("tile", state="normal")

        self.score = 0 
        self.game_score.set("0") 

        self.game_board = [[0] * 4 for _ in range(4)]

        for _ in range(2): 
            while True: 
                x = random.randint(0, 3) 
                y = random.randint(0, 3) 
                if self.game_board[x][y] == 0: 
                    self.game_board[x][y] = 2
                    self.last_spawned_tile = (x, y) 
                    break 
                   
        self.show_board() 

        self.bind_all('<Key>', self.moves)

    # --- Testing with overlay --- 
    def show_overlay(self, title, color): 

        self.canvas.delete("overlay") 

        for i in range(5): 
            self.canvas.create_rectangle(0, 0, 410, 410, fill="#000000", outline="", stipple="gray25" if i % 2 == 0 else "gray50", tags="overlay")
        
        self.canvas.create_rectangle(60, 160, 350, 250, fill="#faf8ef", outline=color, width=4, tags="overlay") 

        self.canvas.create_text(205, 205, text=title, font=("Helvetica", 30, "bold"), fill=color, tags="overlay")

        self.canvas.tag_raise("overlay")

    # --- Check if conditions for game over or win are met --- 
    def game_over(self):  
        for i in range(4): 
            for j in range(4): 
                if self.game_board[i][j] == 2048: 
                    self.game_won() 
                    return True   
         
        for i in range(4): 
            for j in range(4): 
                if self.game_board[i][j] == 0: 
                    return False
                
        for i in range(4): 
            for j in range(3): 
                if self.game_board[i][j] == self.game_board[i][j + 1]: 
                    return False 
                
        for j in range(4): 
            for i in range(3): 
                if self.game_board[i][j] == self.game_board[i + 1][j]: 
                    return False 
                
        self.show_game_over() 
        return True
    
    # --- Shows the game over screen --- 
    def show_game_over(self): 
        if getattr(self, "overlay_active", False): 
            return
        
        self.canvas.itemconfigure("tile", state="hidden")

        self.overlay_active = True 
        self.show_overlay("Game Over", "#776e65")

        self.unbind_all('<Key>')
                 
    # --- Shows the game won screen --- 
    def game_won(self):  
        if getattr(self, "overlay_active", False): 
            return

        self.canvas.itemconfigure("tile", state="hidden")

        self.overlay_active = True 
        self.show_overlay("You Win!", "#edc22e")

        self.unbind_all('<Key>') 

    # --- Resets Overlay to avoid Stacking --- 
    def reset_overlay(self): 
        self.canvas.delete("overlay") 
        self.overlay_active = False

    # --- Define file path and load/save game state ---
    def get_game_state_path(self):
        path = os.path.join(os.path.expanduser("~"), "gamestate.json")
        print("Game state path =", path, type(path)) # So that the User knows what file to delete
        return path

    # --- Load and Save Game State --- 
    def load_game_state(self): 
        path = self.get_game_state_path()

        try:
            with open(path, "r") as f: 
                data = json.load(f)

                self.high_score = data.get("high_score", 0) 
                self.highest_score.set(str(self.high_score)) 

                self.score = data.get("score", 0)
                self.game_score.set(str(self.score)) 

                last_tile = data.get("last_spawned_tile")
                self.last_spawned_tile = tuple(data["last_spawned_tile"]) if data.get("last_spawned_tile") else None

                board = data.get("board") 

                if board and isinstance(board, list) and len(board) == 4: 
                    self.game_board = board 
                else: 
                    self.game_board = [[0]*4 for _ in range(4)] 
                return True 
        except FileNotFoundError: 
            self.high_score = 0 
            self.highest_score.set("0") 
            self.score = 0 
            self.game_score.set("0")
            self.game_board = [[0]*4 for _ in range(4)] 
            return False
        except Exception as e: 
            print(f"ERROR: Failed to load game state! {e}")
            return False 
       
    # --- Save Game State --- 
    def save_game_state(self): 
        path = self.get_game_state_path() 

        data = {
            "high_score": self.high_score,
            "score": self.score,
            "last_spawned_tile": list(self.last_spawned_tile) if self.last_spawned_tile else None,
            "board": self.game_board
        }

        try:
            with open(path, "w") as f:
                json.dump(data, f) 
        except Exception as e: 
            print(f"DEBUG: Error saving high score: {type(e).__name__}: {e}")

    # --- Handle application exit ---
    def on_exit(self):
        self.save_game_state() 
        self.destroy() 

    # --- Toggle Debug Menu --- 
    def toggle_debug_menu(self, event=None): 
        if getattr(self, "debug_visible", False): 
            self.debug_frame.pack_forget() 
            self.debug_visible = False 
            print("DEBUG: Debug Menu was hidden") 
        else:
            self.debug_frame.pack(side="bottom", pady=4) 
            self.debug_visible = True
            print("DEBUG: Debug Menu is visible") 

    # --- DEBUG console function forces win --- 
    def force_win(self):  
 
        self.canvas.delete("overlay") 

        self.canvas.itemconfigure("tile", state="normal")

        self.game_board = [
            [0, 0, 0, 0], 
            [0, 0, 0, 0], 
            [0, 0, 0, 0],
            [0, 0, 0, 2048] 
        ]
        self.score = 0 
        self.show_board() 
        self.game_won() 

    # --- DEBUG function forces loose --- 
    def force_game_over(self):
        
        self.canvas.delete("overlay") 

        self.canvas.itemconfigure("tile", state="normal")

        self.game_board = [
            [2, 4, 8, 16],
            [32, 64, 128, 256],
            [512, 1024, 2, 4],
            [8, 16, 32, 64]
    ]
        self.score = 0
        self.show_board()
        self.game_over()
   
# --- Run the App --- 
if __name__ == "__main__": 
    app = play_2048()
    app.bind_all('<Key>', app.moves)
    app.wm_title("2048")
    app.minsize(430, 470)
    app.mainloop()                                     