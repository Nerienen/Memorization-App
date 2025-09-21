import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import random
import csv
import json
import os
import sys
import subprocess

# -------- Data Handling --------
QUESTIONS = {}
queue = []
wrong_queue = []
current_question = None
options = []

# Progress tracking
answered_count = 0
total_questions = 0
answered_questions_set = set()  # track questions already counted

BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
PROGRESS_FILE = os.path.join(BASE_DIR, "quiz_progress.json")
LAST_CSV_FILE = os.path.join(BASE_DIR, "last_csv.json")  # store last CSV path

def load_questions_from_csv(file_path):
    questions = {}
    try:
        with open(file_path, newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    q = row[0].strip()
                    a = row[1].strip()
                    img = row[2].strip() if len(row) >= 3 else None
                    questions[q] = (a, img)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load CSV:\n{e}")
        return {}
    return questions

def save_progress():
    data = {
        "answered_count": answered_count,
        "total_questions": total_questions,
        "answered_questions": list(answered_questions_set),
        "queue": [q for q, _ in queue],
        "wrong_queue": [q for q, _ in wrong_queue]
    }
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Failed to save progress: {e}")

def save_last_csv(file_path):
    try:
        with open(LAST_CSV_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_csv": file_path}, f)
    except Exception as e:
        print(f"Failed to save last CSV: {e}")

def load_last_csv():
    if os.path.exists(LAST_CSV_FILE):
        try:
            with open(LAST_CSV_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_csv", None)
        except:
            return None
    return None

def reset_quiz(new_questions):
    global QUESTIONS, queue, wrong_queue, current_question, options
    global answered_count, total_questions, answered_questions_set
    QUESTIONS = new_questions
    queue = list(QUESTIONS.items())
    random.shuffle(queue)
    wrong_queue = []
    current_question = None
    options = []

    clear_frame(question_frame)
    clear_frame(feedback_frame)
    for btn in option_frames:
        clear_frame(btn)
    clear_frame(progress_inner)

    answered_count = 0
    answered_questions_set = set()
    total_questions = len(new_questions)
    progress_bar["maximum"] = total_questions
    progress_bar["value"] = 0
    progress_text.config(text=f"0 / {total_questions}")

    # Load previous progress if exists
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                answered_count = data.get("answered_count", 0)
                answered_questions_set = set(data.get("answered_questions", []))
                progress_bar["value"] = answered_count
                progress_text.config(text=f"{answered_count} / {total_questions}")

                answered_set = set(data.get("answered_questions", []))
                queue = [(q, QUESTIONS[q]) for q, _ in queue if q not in answered_set]
                wrong_queue = [(q, QUESTIONS[q]) for q in data.get("wrong_queue", []) if q in QUESTIONS]
        except Exception as e:
            print(f"Failed to load progress: {e}")

    if QUESTIONS:
        ask_question()

# -------- Math Rendering --------
def render_math_latex(text, master, fontsize=16, color="black", max_width=8):
    fig, ax = plt.subplots(figsize=(max_width, 1))
    txt = ax.text(0.5, 0.5, text, fontsize=fontsize, ha='center', va='center', color=color, wrap=True)
    ax.axis('off')
    fig.canvas.draw()
    bbox = txt.get_window_extent(renderer=fig.canvas.get_renderer())
    width, height = bbox.width / fig.dpi, bbox.height / fig.dpi
    fig.set_size_inches(width * 1.1, height * 1.2)
    fig.tight_layout(pad=0.2)
    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.pack()
    plt.close(fig)
    return widget

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

# -------- Quiz Logic --------
def ask_question():
    global current_question, options, answered_count
    feedback_frame.pack_forget()
    bottom_frame.pack_forget()
    clear_frame(question_frame)
    for btn in option_frames:
        clear_frame(btn)

    if not queue and not wrong_queue:
        render_math_latex(r"$\text{All done!}$", question_frame, fontsize=20)
        return

    if not queue and wrong_queue:
        queue.extend(wrong_queue)
        wrong_queue.clear()
        random.shuffle(queue)

    current_question = queue.pop(0)
    func, (correct, image) = current_question

    # Increment progress only once per question
    if func not in answered_questions_set:
        answered_questions_set.add(func)
        answered_count += 1
        progress_bar["value"] = answered_count
        progress_text.config(text=f"{answered_count} / {total_questions}")
        save_progress()

    wrong_answers = random.sample(
        [v[0] for _, v in QUESTIONS.items() if v[0] != correct],
        min(3, len(QUESTIONS) - 1)
    )
    options = wrong_answers + [correct]
    random.shuffle(options)

    render_math_latex(rf" {func} ?", question_frame, fontsize=20)

    if image:
        try:
            from PIL import Image, ImageTk
            import requests
            from io import BytesIO
            if image.startswith("http"):
                response = requests.get(image)
                img_data = BytesIO(response.content)
                img = Image.open(img_data)
            else:
                img = Image.open(image)
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            img_label = tk.Label(question_frame, image=tk_img)
            img_label.image = tk_img
            img_label.pack(pady=10)
        except Exception as e:
            tk.Label(question_frame, text=f"[Image load failed: {e}]", fg="red").pack()

    for i, opt in enumerate(options):
        btn_widget = render_math_latex(opt, option_frames[i], fontsize=16)
        btn_widget.config(cursor="hand2")
        btn_widget.bind("<Button-1>", lambda e, o=opt: check_answer(o))

def check_answer(selected):
    func, (correct, image) = current_question
    clear_frame(feedback_frame)
    if selected == correct:
        render_math_latex(rf"✔ Correct, {func} → {correct}", feedback_frame, fontsize=18, color="green")
        log_progress(func, correct, True)
    else:
        render_math_latex(rf"✘ Wrong, {func} → {correct}", feedback_frame, fontsize=18, color="red")
        wrong_queue.append(current_question)
        log_progress(func, correct, False)

    feedback_frame.pack(pady=10)
    bottom_frame.pack(pady=5)

# -------- Progress Panel --------
def log_progress(question, answer, correct_flag):
    color = "green" if correct_flag else "red"
    entry_label = tk.Label(progress_inner, text=f"{question} → {answer}", fg=color, bg="#f0f0f0",
                           anchor="w", justify="left", wraplength=220)
    entry_label.pack(pady=2, anchor="w")

# -------- GUI Setup --------
root = tk.Tk()
root.title("Derivative Trainer")
root.state("zoomed")
try:
    root.attributes("-zoomed", True)
except:
    pass

# Menu bar
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)

def open_csv():
    file_path = filedialog.askopenfilename(title="Select CSV file",
                                           filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if file_path:
        save_last_csv(file_path)  # save CSV path
        new_q = load_questions_from_csv(file_path)
        if new_q:
            reset_quiz(new_q)

def open_progress_folder():
    folder_path = os.path.dirname(PROGRESS_FILE)
    if not os.path.exists(folder_path):
        messagebox.showerror("Error", f"Folder does not exist:\n{folder_path}")
        return
    try:
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        else:  # Linux
            subprocess.Popen(["xdg-open", folder_path])
    except Exception as e:
        messagebox.showerror("Error", f"Could not open folder:\n{e}")

file_menu.add_command(label="Load CSV...", command=open_csv)
file_menu.add_command(label="Open Progress Folder", command=open_progress_folder)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=file_menu)
root.config(menu=menubar)

# Scrollable root
main_canvas = tk.Canvas(root, highlightthickness=0)
main_canvas.pack(fill=tk.BOTH, expand=True)
scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
scrollbar.pack(side=tk.RIGHT, fill="y")
main_canvas.configure(yscrollcommand=scrollbar.set)
outer_frame = tk.Frame(main_canvas)
main_canvas.create_window((0, 0), window=outer_frame, anchor="nw")
outer_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))

def _on_mousewheel(event):
    main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
main_canvas.bind_all("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))
main_canvas.bind_all("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))

# Layout
main_frame = tk.Frame(outer_frame)
main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
question_frame = tk.Frame(main_frame)
question_frame.pack(pady=20)

option_frames = []
for _ in range(4):
    frame = tk.Frame(main_frame)
    frame.pack(pady=5)
    option_frames.append(frame)

feedback_frame = tk.Frame(main_frame)
bottom_frame = tk.Frame(main_frame)
next_button = tk.Button(bottom_frame, text="Next →", font=("Arial", 12), command=ask_question)
next_button.pack()

# Progress panel
progress_frame = tk.Frame(outer_frame, width=250, bg="#f0f0f0")
progress_frame.pack(side=tk.RIGHT, fill=tk.Y)
progress_label = tk.Label(progress_frame, text="Progress", font=("Arial", 12, "bold"), bg="#f0f0f0")
progress_label.pack(pady=10)
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=200, mode="determinate")
progress_bar.pack(pady=5)
progress_text = tk.Label(progress_frame, text="0 / 0", font=("Arial", 10), bg="#f0f0f0")
progress_text.pack(pady=5)
progress_inner = tk.Frame(progress_frame, bg="#f0f0f0")
progress_inner.pack(fill=tk.BOTH, expand=True)

# Auto-load last CSV if exists
last_csv = load_last_csv()
if last_csv and os.path.exists(last_csv):
    new_q = load_questions_from_csv(last_csv)
    if new_q:
        reset_quiz(new_q)

# Start
root.mainloop()
