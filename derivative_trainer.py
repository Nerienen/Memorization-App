import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import random

# Question bank: LaTeX format
QUESTIONS = {
    r"$x^2$": r"$2x$",
    r"$x^3$": r"$3x^2$",
    r"$\sin(x)$": r"$\cos(x)$",
    r"$\cos(x)$": r"$-\sin(x)$",
    r"$e^x$": r"$e^x$",
    r"$\ln(x)$": r"$\frac{1}{x}$",
    r"$\sqrt{x}$": r"$\frac{1}{2\sqrt{x}}$",
    r"$\tan(x)$": r"$\sec^2(x)$",
    r"$\sec(x)$": r"$\sec(x)\tan(x)$",
    r"$\csc(x)$": r"$-\csc(x)\cot(x)$",
}

queue = list(QUESTIONS.items())
random.shuffle(queue)
wrong_queue = []
current_question = None
options = []

def render_math_latex(text, master, fontsize=20, fig_width=5, fig_height=0.6, color="black"):
    """Render text (can include LaTeX segments) inside a Tk frame using Matplotlib; return the widget."""
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.text(0.5, 0.5, text, fontsize=fontsize, ha='center', va='center', color=color)
    ax.axis('off')
    fig.tight_layout(pad=0.2)
    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.pack()
    return widget

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def ask_question():
    global current_question, options
    feedback_frame.pack_forget()
    bottom_frame.pack_forget()  # hide Next button until answer chosen
    clear_frame(question_frame)
    for btn in option_frames:
        clear_frame(btn)

    if not queue and not wrong_queue:
        render_math_latex(r"$\text{All done!}$", question_frame, fontsize=25, fig_width=6)
        return

    if not queue and wrong_queue:
        queue.extend(wrong_queue)
        wrong_queue.clear()
        random.shuffle(queue)

    current_question = queue.pop(0)
    func, correct = current_question

    wrong_answers = random.sample([v for _, v in QUESTIONS.items() if v != correct], 3)
    options = wrong_answers + [correct]
    random.shuffle(options)

    render_math_latex(rf"Derivative of {func} ?", question_frame, fontsize=25, fig_width=7, fig_height=0.9)

    for i, opt in enumerate(options):
        btn_widget = render_math_latex(opt, option_frames[i], fontsize=18, fig_width=3.5, fig_height=0.7)
        btn_widget.config(cursor="hand2")
        btn_widget.bind("<Button-1>", lambda e, o=opt: check_answer(o))

def check_answer(selected):
    func, correct = current_question
    clear_frame(feedback_frame)
    if selected == correct:
        render_math_latex(rf"✔ Correct, {func} → {correct}", feedback_frame,
                          fontsize=18, fig_width=7, fig_height=0.9, color="green")
        log_progress(func, True)
    else:
        render_math_latex(rf"✘ Wrong, {func} → {correct}", feedback_frame,
                          fontsize=18, fig_width=7, fig_height=0.9, color="red")
        wrong_queue.append(current_question)
        log_progress(func, False)

    feedback_frame.pack(pady=10)
    bottom_frame.pack(pady=5)  # show Next button

def log_progress(question, correct):
    progress_box.config(state="normal")
    tag = "correct" if correct else "wrong"
    progress_box.insert(tk.END, f"{question}\n", tag)
    progress_box.tag_config("correct", foreground="green")
    progress_box.tag_config("wrong", foreground="red")
    progress_box.config(state="disabled")

# --- GUI Setup ---
root = tk.Tk()
root.title("Derivative Trainer")
root.geometry("850x550")  # wider for progress panel

# Main area (left)
main_frame = tk.Frame(root)
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
next_button = tk.Button(bottom_frame, text="Next →", font=("Arial", 14), command=ask_question)
next_button.pack()

# Progress panel (right)
progress_frame = tk.Frame(root, width=200, bg="#f0f0f0")
progress_frame.pack(side=tk.RIGHT, fill=tk.Y)

progress_label = tk.Label(progress_frame, text="Progress", font=("Arial", 14, "bold"), bg="#f0f0f0")
progress_label.pack(pady=10)

progress_box = tk.Text(progress_frame, width=20, height=25, state="disabled", bg="white")
progress_box.pack(padx=5, pady=5)

ask_question()
root.mainloop()


#okay good, now can you make it so the stuff on the right pannel appears as math formatted? right now i see $ signs