"""Simple beginner-friendly Tkinter GUI for the four-module pipeline."""
import tkinter as tk
from tkinter import scrolledtext
from pipeline import ConversionPipeline

def launch() -> None:
    pipeline = ConversionPipeline()
    root = tk.Tk()
    root.title("Unit Converter Assistant")
    root.geometry("760x520")
    tk.Label(root, text="Unit Converter Assistant", font=("Segoe UI", 18, "bold")).pack(pady=10)
    tk.Label(root, text="Ask naturally: Convert 10 kilometers to miles").pack()
    entry = tk.Entry(root, font=("Segoe UI", 12), width=70)
    entry.pack(pady=8)
    output = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20, font=("Consolas", 10))
    output.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
    def ask(event=None):
        query = entry.get().strip()
        if not query: return
        response, details = pipeline.ask(query)
        output.insert(tk.END, f"You: {query}\nTrace: {' -> '.join(details['trace'])}\nAssistant: {response}\n\n")
        output.see(tk.END); entry.delete(0, tk.END)
    tk.Button(root, text="Convert", command=ask, width=14).pack(pady=5)
    entry.bind("<Return>", ask)
    root.mainloop()

if __name__ == "__main__":
    launch()
