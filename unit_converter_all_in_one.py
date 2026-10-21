"""Single-file four-module unit converter with terminal demo and Tkinter GUI."""
import argparse, math, re
from dataclasses import dataclass
from pathlib import Path

UNITS={"length":{"meter":("meter",1),"meters":("meter",1),"m":("meter",1),"kilometer":("kilometer",1000),"kilometers":("kilometer",1000),"km":("kilometer",1000),"mile":("mile",1609.344),"miles":("mile",1609.344),"mi":("mile",1609.344),"foot":("foot",.3048),"feet":("foot",.3048),"ft":("foot",.3048),"inch":("inch",.0254),"inches":("inch",.0254),"in":("inch",.0254),"centimeter":("centimeter",.01),"centimeters":("centimeter",.01),"cm":("centimeter",.01)},"weight":{"kilogram":("kilogram",1000),"kilograms":("kilogram",1000),"kg":("kilogram",1000),"gram":("gram",1),"grams":("gram",1),"g":("gram",1),"pound":("pound",453.59237),"pounds":("pound",453.59237),"lb":("pound",453.59237),"ounce":("ounce",28.349523125),"ounces":("ounce",28.349523125),"oz":("ounce",28.349523125),"quintal":("quintal",100000),"stone":("stone",6350.29318)}}

def resolve(u):
    if not isinstance(u,str): return None
    u=u.strip().lower().replace(".","")
    for category, aliases in UNITS.items():
        if u in aliases: return (category,*aliases[u])
    return None

def rag_lookup(u):
    """Resolve aliases using the local reference_units.md sheet."""
    key = str(u).strip().lower().replace(".", "")
    aliases = {"quintals":"quintal", "stones":"stone", "st":"stone",
               "kilometre":"kilometer", "kilometres":"kilometers",
               "metre":"meter", "metres":"meters"}
    sheet = Path(__file__).with_name("reference_units.md")
    if sheet.exists() and (key in sheet.read_text(encoding="utf-8").lower() or key in aliases):
        key = aliases.get(key, key)
    return resolve(key)

try:
    from langchain.tools import tool
except ImportError:
    tool=lambda f:f

@tool
def convert_units(value:float, from_unit:str, to_unit:str)->str:
    """Convert length/weight. Both units are required; never guess a missing source. Includes quintal and stone."""
    try: value=float(value)
    except (TypeError,ValueError): return "Error: value must be numeric."
    if not math.isfinite(value): return "Error: value must be finite."
    a,b=rag_lookup(from_unit),rag_lookup(to_unit)
    if not a: return f"Error: unsupported source unit '{from_unit}'."
    if not b: return f"Error: unsupported target unit '{to_unit}'."
    if a[0]!=b[0]: return f"Error: incompatible conversion from {a[1]} to {b[1]}."
    return f"{value:g} {a[1]} = {value*a[2]/b[2]:.10g} {b[1]}"

class Memory:
    def __init__(self): self.preference="metric"; self.last=None
    def set(self,x): self.preference=x.lower(); return f"Preference set to {self.preference}."
    def default_target(self, category):
        return "kilogram" if category=="weight" and self.preference=="metric" else "pound" if category=="weight" else "meter" if self.preference=="metric" else "foot"
    def follow(self,q):
        if q.lower().startswith(("now ","and ")) and self.last:
            for w in reversed(re.findall("[A-Za-z]+",q.lower())):
                if w not in {"now","and","in","to"} and rag_lookup(w): return self.last[0],self.last[1],w

@dataclass
class Parsed: value:float|None; source:str|None; target:str|None; question:str|None=None
class Parser:
    def parse(self,q,default_target=None):
        n=re.search(r"[-+]?\d+(?:\.\d+)?",q); value=float(n.group()) if n else None
        units=[w for w in re.findall("[A-Za-z]+",q.lower()) if rag_lookup(w)]
        if value is None:return Parsed(None,None,None,"Please provide a numeric value.")
        if len(units)<2:
            if units and "to" not in q.lower() and default_target:
                return Parsed(value,units[0],default_target)
            return Parsed(value,None,units[0] if units else None,"What is the source unit? I will not guess it.")
        # In “how many kilograms are 5000 grams?”, the unit before “are” is target.
        m=re.search(r"how many\s+([a-z]+)\s+are\s+[-+]?\d",q.lower())
        if m and len(units)>=2:return Parsed(value,units[-1],units[0])
        return Parsed(value,units[-2],units[-1])

class Checker:
    def verify(self,value,source,target,result):
        m=re.search(r"=\s*([-+]?\d+(?:\.\d+)?)",result)
        if not m:return "Checker could not verify the result."
        back=convert_units.invoke({"value":float(m.group(1)),"from_unit":target,"to_unit":source})
        b=re.search(r"=\s*([-+]?\d+(?:\.\d+)?)",back)
        if b and abs(float(b.group(1))-value)<=1e-6*max(1,abs(value)):return "Reverse check passed."
        return "Reverse check caught a possible conversion error."

class Pipeline:
    def __init__(self):self.memory=Memory();self.parser=Parser();self.checker=Checker()
    def ask(self,q):
        f=self.memory.follow(q); text=f"{f[0]} {f[1]} to {f[2]}" if f else q
        hinted=next((rag_lookup(w) for w in re.findall("[A-Za-z]+",text.lower()) if rag_lookup(w)),None)
        p=self.parser.parse(text,self.memory.default_target(hinted[0]) if hinted else None); trace=["HumanMessage","ParserAgent"]
        if p.question:return p.question,trace+["Clarification"]
        result=convert_units.invoke({"value":p.value,"from_unit":p.source,"to_unit":p.target});self.memory.last=(p.value,p.source)
        return result+"\n"+self.checker.verify(p.value,p.source,p.target,result),trace+["ConverterAgent","CheckerAgent(reverse)","FinalResponse"]

def demo():
    p=Pipeline(); print("="*50+"\nUNIT CONVERTER ASSISTANT\n"+"="*50)
    for q in ["Convert 10 kilometers to miles.","How many kilograms are 5000 grams?","Convert 12 inches to centimeters.","Convert 5 to kg."]:
        r,t=p.ask(q); print(f"\nUser: {q}\nTrace: {' -> '.join(t)}\nAssistant: {r}")

def evidence():
    """Show the checker catching a deliberately corrupted forward result."""
    checker=Checker(); wrong="10 kilometer = 5 mile"
    print("EVIDENCE: deliberate wrong conversion"); print("Forward result:",wrong)
    print("Checker:",checker.verify(10,"kilometer","mile",wrong))
    p=Pipeline(); print("\nEVIDENCE: ambiguity before tool call")
    print(p.ask("Convert 5 to kg."))

def chat():
    p=Pipeline()
    while True:
        q=input("\nYou: ").strip()
        if q.lower() in {"quit","exit"}: break
        if q.lower() in {"metric","imperial"}: print(p.memory.set(q)); continue
        r,t=p.ask(q); print("Trace: "+" -> ".join(t)+"\nAssistant: "+r)

def gui():
    import tkinter as tk
    from tkinter import scrolledtext
    p=Pipeline(); root=tk.Tk(); root.title("Unit Converter Assistant - 4 Agent Pipeline"); root.geometry("900x650")
    tk.Label(root,text="UNIT CONVERTER ASSISTANT",font=("Segoe UI",18,"bold")).pack(pady=8)
    tk.Label(root,text="Memory/RAG  →  Parser Agent  →  Converter Tool  →  Checker Agent",font=("Segoe UI",11)).pack()
    preference_bar=tk.Frame(root); preference_bar.pack(pady=6)
    tk.Label(preference_bar,text="Preferred unit system:").pack(side=tk.LEFT,padx=4)
    preference=tk.StringVar(value="metric")
    tk.OptionMenu(preference_bar,preference,"metric","imperial").pack(side=tk.LEFT)
    preference_status=tk.Label(preference_bar,text="Current: metric")
    preference_status.pack(side=tk.LEFT,padx=8)
    def save_preference():
        message=p.memory.set(preference.get())
        preference_status.config(text="Current: "+p.memory.preference)
        out.insert(tk.END,"MEMORY: "+message+"\nFuture default units will use this system.\n\n")
    tk.Button(preference_bar,text="Save Preference",command=save_preference).pack(side=tk.LEFT,padx=4)
    stages=tk.Frame(root); stages.pack(pady=8)
    stage_labels=[]
    for name in ("1. Memory + RAG", "2. Parser Agent", "3. Converter Tool", "4. Checker Agent"):
        label=tk.Label(stages,text=name+"\nWaiting",width=19,height=2,bg="#e6e6e6",relief=tk.GROOVE)
        label.pack(side=tk.LEFT,padx=4); stage_labels.append(label)
    entry=tk.Entry(root,width=85);entry.pack(pady=8); out=scrolledtext.ScrolledText(root,height=22);out.pack(fill=tk.BOTH,expand=True,padx=10)
    def ask(e=None):
        q=entry.get().strip()
        if q:
            for label in stage_labels: label.config(bg="#fff2cc")
            r,t=p.ask(q)
            clarification = "Clarification" in t
            stage_labels[0].config(text="1. Memory + RAG\nPreference/history loaded",bg="#d9ead3")
            stage_labels[1].config(text="2. Parser Agent\n"+("Clarification asked" if clarification else "Value + units extracted"),bg="#fce5cd")
            stage_labels[2].config(text="3. Converter Tool\n"+("Not called" if clarification else "Conversion completed"),bg="#d9ead3" if not clarification else "#f4cccc")
            stage_labels[3].config(text="4. Checker Agent\n"+("Waiting" if clarification else ("Reverse check shown")),bg="#d9ead3" if not clarification else "#fff2cc")
            out.insert(tk.END,f"USER QUERY: {q}\n\nVISIBLE AGENT TRACE:\n  {' -> '.join(t)}\n\nTOOL / CHECKER OUTPUT:\n{r}\n\n{'='*70}\n\n");out.see(tk.END);entry.delete(0,tk.END)
    def show_evidence():
        wrong="10 kilometer = 5 mile"
        result=p.checker.verify(10,"kilometer","mile",wrong)
        out.insert(tk.END,f"EVIDENCE - deliberate wrong conversion\nForward result: {wrong}\nChecker result: {result}\n\n")
        out.see(tk.END)
    buttons=tk.Frame(root);buttons.pack(pady=6)
    tk.Button(buttons,text="Run Query",command=ask,width=16).pack(side=tk.LEFT,padx=4)
    tk.Button(buttons,text="Show Wrong-Result Evidence",command=show_evidence,width=25).pack(side=tk.LEFT,padx=4)
    entry.bind("<Return>",ask);root.mainloop()

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--demo",action="store_true");ap.add_argument("--chat",action="store_true");ap.add_argument("--evidence",action="store_true");a=ap.parse_args()
    evidence() if a.evidence else demo() if a.demo else chat() if a.chat else gui()
