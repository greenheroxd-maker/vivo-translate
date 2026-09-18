import tkinter as tk
from tkinter import ttk, messagebox
import threading, time, json, os, re
from pathlib import Path

APP='Game Live Translator'
CACHE=Path.home()/'.game_live_translator_cache.json'

try:
    from PIL import ImageGrab
    import pytesseract
    from deep_translator import GoogleTranslator
except Exception as e:
    IMPORT_ERROR=str(e)
else:
    IMPORT_ERROR=None

class App:
    def __init__(self, root):
        self.root=root; root.title(APP); root.geometry('520x355'); root.resizable(False,False)
        self.region=None; self.running=False; self.last=''; self.cache=self.load_cache()
        self.translator=GoogleTranslator(source='auto', target='es') if not IMPORT_ERROR else None
        f=ttk.Frame(root,padding=18); f.pack(fill='both',expand=True)
        ttk.Label(f,text=APP,font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(f,text='Seleccioná el cuadro de diálogo del juego y traducilo en vivo.').pack(anchor='w',pady=(2,14))
        row=ttk.Frame(f); row.pack(fill='x')
        ttk.Button(row,text='1. Seleccionar zona',command=self.select_region).pack(side='left')
        self.reglabel=ttk.Label(row,text='  Zona: no seleccionada'); self.reglabel.pack(side='left')
        row2=ttk.Frame(f); row2.pack(fill='x',pady=12)
        ttk.Label(row2,text='Idioma OCR:').pack(side='left')
        self.lang=tk.StringVar(value='eng')
        ttk.Combobox(row2,textvariable=self.lang,values=['eng','spa'],width=8,state='readonly').pack(side='left',padx=6)
        self.btn=ttk.Button(f,text='2. INICIAR TRADUCCIÓN',command=self.toggle); self.btn.pack(fill='x',ipady=8)
        self.status=ttk.Label(f,text='Detenido'); self.status.pack(anchor='w',pady=(10,4))
        ttk.Label(f,text='Última traducción:').pack(anchor='w')
        self.preview=tk.Text(f,height=7,wrap='word'); self.preview.pack(fill='x'); self.preview.configure(state='disabled')
        ttk.Label(f,text='Requiere Internet. El texto traducido aparece en una ventana flotante.',font=('Segoe UI',8)).pack(anchor='w',pady=(8,0))
        self.overlay=tk.Toplevel(root); self.overlay.withdraw(); self.overlay.overrideredirect(True); self.overlay.attributes('-topmost',True)
        self.overlay.attributes('-alpha',0.92)
        self.olabel=tk.Label(self.overlay,text='',font=('Segoe UI',16,'bold'),bg='#111111',fg='white',wraplength=850,justify='left',padx=16,pady=10)
        self.olabel.pack()
        self.overlay.bind('<Button-1>',lambda e:self.overlay.withdraw())
        root.protocol('WM_DELETE_WINDOW',self.close)
        if IMPORT_ERROR: messagebox.showerror(APP,'Faltan componentes internos:\n'+IMPORT_ERROR)

    def load_cache(self):
        try: return json.loads(CACHE.read_text(encoding='utf-8'))
        except: return {}
    def save_cache(self):
        try: CACHE.write_text(json.dumps(self.cache,ensure_ascii=False,indent=2),encoding='utf-8')
        except: pass

    def select_region(self):
        self.root.withdraw(); time.sleep(.2)
        sel=tk.Toplevel(); sel.attributes('-fullscreen',True); sel.attributes('-alpha',0.25); sel.attributes('-topmost',True); sel.configure(bg='black')
        c=tk.Canvas(sel,cursor='cross',highlightthickness=0); c.pack(fill='both',expand=True)
        data={}
        def down(e): data['x']=e.x; data['y']=e.y; data['r']=c.create_rectangle(e.x,e.y,e.x,e.y,outline='red',width=3)
        def move(e):
            if 'r' in data: c.coords(data['r'],data['x'],data['y'],e.x,e.y)
        def up(e):
            x1,y1,x2,y2=data['x'],data['y'],e.x,e.y
            self.region=(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2))
            sel.destroy(); self.root.deiconify(); self.reglabel.config(text=f'  Zona: {self.region[2]-self.region[0]}×{self.region[3]-self.region[1]} px')
        c.bind('<ButtonPress-1>',down); c.bind('<B1-Motion>',move); c.bind('<ButtonRelease-1>',up)
        sel.bind('<Escape>',lambda e:(sel.destroy(),self.root.deiconify()))

    def toggle(self):
        if self.running:
            self.running=False; self.btn.config(text='2. INICIAR TRADUCCIÓN'); self.status.config(text='Detenido'); self.overlay.withdraw(); return
        if IMPORT_ERROR: return
        if not self.region: messagebox.showinfo(APP,'Primero seleccioná la zona donde aparece el diálogo.'); return
        self.running=True; self.btn.config(text='DETENER'); self.status.config(text='Leyendo pantalla…')
        threading.Thread(target=self.loop,daemon=True).start()

    def clean(self,s):
        s=s.replace('|','I'); s=re.sub(r'\s+',' ',s).strip()
        return s
    def loop(self):
        while self.running:
            try:
                img=ImageGrab.grab(bbox=self.region)
                text=self.clean(pytesseract.image_to_string(img,lang=self.lang.get(),config='--psm 6'))
                if len(text)>=2 and text!=self.last:
                    self.last=text; self.root.after(0,lambda t=text:self.status.config(text='Traduciendo: '+t[:55]))
                    tr=self.cache.get(text)
                    if not tr:
                        tr=self.translator.translate(text); self.cache[text]=tr; self.save_cache()
                    self.root.after(0,lambda t=tr:self.show_translation(t))
            except Exception as e:
                self.root.after(0,lambda s=str(e):self.status.config(text='Error: '+s[:80]))
                time.sleep(3)
            time.sleep(0.8)
    def show_translation(self,t):
        self.preview.configure(state='normal'); self.preview.delete('1.0','end'); self.preview.insert('1.0',t); self.preview.configure(state='disabled')
        self.olabel.config(text=t); self.overlay.update_idletasks()
        x=self.region[0]; y=max(0,self.region[1]-self.overlay.winfo_reqheight()-8)
        self.overlay.geometry(f'+{x}+{y}'); self.overlay.deiconify()
        self.status.config(text='Activo — esperando que cambie el diálogo…')
    def close(self):
        self.running=False; self.save_cache(); self.root.destroy()

if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
