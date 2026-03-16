# processador_lote/gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from datetime import datetime
import os
import sys

# Adicionar o diretório pai ao path para importar extrator_contajur
sys.path.insert(0, str(Path(__file__).parent.parent))

from extrator_contajur.auxiliares.pdf_reader import read_pdf
from extrator_contajur.auxiliares.pdf_reader2 import read_pdf2
from extrator_contajur.banco import get_processor
from extrator_contajur.auxiliares.xml_to_csv import xml_to_csv
from extrator_contajur.auxiliares.renomeador import RenomeadorExtrato


class BatchProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Processador em Lote de Extratos Bancários")
        self.root.geometry("900x650")
        self.root.resizable(True, True)
        
        self.input_folders = []  # Lista de pastas de entrada
        self.is_processing = False
        self.renomeador = RenomeadorExtrato()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface do usuário"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # --- Frame de pastas de entrada ---
        folders_frame = ttk.LabelFrame(main_frame, text="Pastas de Entrada", padding="5")
        folders_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        folders_frame.columnconfigure(0, weight=1)
        folders_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=2)

        # Listbox com scrollbar para as pastas
        list_frame = ttk.Frame(folders_frame)
        list_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.folders_listbox = tk.Listbox(list_frame, height=6, selectmode=tk.EXTENDED)
        folders_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.folders_listbox.yview)
        self.folders_listbox.configure(yscrollcommand=folders_scrollbar.set)
        self.folders_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        folders_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Botões para gerenciar pastas
        folders_btn_frame = ttk.Frame(folders_frame)
        folders_btn_frame.grid(row=1, column=0, columnspan=2, pady=5)

        ttk.Button(folders_btn_frame, text="Adicionar Pasta", command=self.add_input_folder).grid(row=0, column=0, padx=5)
        ttk.Button(folders_btn_frame, text="Remover Selecionada(s)", command=self.remove_selected_folders).grid(row=0, column=1, padx=5)
        ttk.Button(folders_btn_frame, text="Limpar Tudo", command=self.clear_folders).grid(row=0, column=2, padx=5)

        self.folders_count_label = ttk.Label(folders_frame, text="Nenhuma pasta adicionada", foreground="gray")
        self.folders_count_label.grid(row=2, column=0, columnspan=2, pady=2)

        # Nota sobre saída
        note_frame = ttk.Frame(main_frame)
        note_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(note_frame, text="Os CSVs gerados serão salvos na mesma pasta do PDF de origem.", 
                  foreground="gray").grid(row=0, column=0, sticky=tk.W)

        # --- Botões de ação ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=5)
        
        self.process_btn = ttk.Button(button_frame, text="Processar", command=self.start_processing)
        self.process_btn.grid(row=0, column=0, padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancelar", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_btn.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Limpar Log", command=self.clear_log).grid(row=0, column=2, padx=5)
        
        # --- Barra de progresso ---
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0 / 0 arquivos processados")
        self.progress_label.grid(row=1, column=0, pady=2)
        
        # --- Área de log ---
        log_frame = ttk.LabelFrame(main_frame, text="Log de Processamento", padding="5")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=3)
        
        self.log_text = tk.Text(log_frame, height=15, width=80, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("warning", foreground="orange")

    # ── Gerenciamento de pastas ──────────────────────────────────────────────

    def add_input_folder(self):
        """Abre diálogo para adicionar uma pasta de entrada"""
        folder = filedialog.askdirectory(title="Selecione uma pasta com PDFs")
        if not folder:
            return
        if folder in self.input_folders:
            messagebox.showwarning("Aviso", "Essa pasta já foi adicionada.")
            return
        self.input_folders.append(folder)
        self.folders_listbox.insert(tk.END, folder)
        self._update_folders_label()
        self.log_message(f"Pasta adicionada: {folder}", "info")

    def remove_selected_folders(self):
        """Remove as pastas selecionadas na listbox"""
        selected = list(self.folders_listbox.curselection())
        if not selected:
            return
        for index in reversed(selected):
            removed = self.input_folders.pop(index)
            self.folders_listbox.delete(index)
            self.log_message(f"Pasta removida: {removed}", "warning")
        self._update_folders_label()

    def clear_folders(self):
        """Remove todas as pastas"""
        self.input_folders.clear()
        self.folders_listbox.delete(0, tk.END)
        self._update_folders_label()

    def _update_folders_label(self):
        count = len(self.input_folders)
        if count == 0:
            self.folders_count_label.config(text="Nenhuma pasta adicionada", foreground="gray")
        else:
            self.folders_count_label.config(text=f"{count} pasta(s) adicionada(s)", foreground="black")

    # ── Log ─────────────────────────────────────────────────────────────────

    def log_message(self, message, tag="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    # ── Processamento ────────────────────────────────────────────────────────
        
    def start_processing(self):
        """Inicia o processamento em lote"""
        if not self.input_folders:
            messagebox.showerror("Erro", "Adicione pelo menos uma pasta de entrada!")
            return

        # Coletar todos os PDFs de todas as pastas
        pdf_files = []
        for folder in self.input_folders:
            if not os.path.exists(folder):
                self.log_message(f"Pasta não encontrada, ignorada: {folder}", "warning")
                continue
            found = list(Path(folder).glob("*.pdf"))
            self.log_message(f"{len(found)} PDF(s) encontrado(s) em: {folder}", "info")
            pdf_files.extend(found)

        if not pdf_files:
            messagebox.showwarning("Aviso", "Nenhum arquivo PDF encontrado nas pastas selecionadas!")
            return
            
        self.log_message(f"Total: {len(pdf_files)} arquivo(s) PDF para processar", "info")
        self.log_message("=" * 60, "info")
        
        self.process_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.is_processing = True
        
        thread = threading.Thread(target=self.process_files, args=(pdf_files,), daemon=True)
        thread.start()
        
    def cancel_processing(self):
        self.is_processing = False
        self.log_message("Processamento cancelado pelo usuário", "warning")
        self.process_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        
    def process_files(self, pdf_files):
        """Processa todos os arquivos PDF, salvando o CSV na mesma pasta do PDF"""
        total_files = len(pdf_files)
        successful = 0
        failed = 0
        
        self.progress_bar['maximum'] = total_files
        self.progress_bar['value'] = 0
        
        for index, pdf_file in enumerate(pdf_files, 1):
            if not self.is_processing:
                break
                
            self.log_message(f"\n[{index}/{total_files}] Processando: {pdf_file.name}", "info")
            
            # A saída é sempre a mesma pasta do PDF de origem
            output_folder = pdf_file.parent
            
            try:
                with open(pdf_file, 'rb') as file:
                    text, identified_bank = read_pdf(file)
                    
                    if not text or identified_bank.startswith("Erro") or identified_bank == "Banco não identificado":
                        self.log_message(f"Banco não identificado", "error")
                        failed += 1
                        continue
                    
                    self.log_message(f"   Banco identificado: {identified_bank}", "info")
                    
                    if identified_bank in ['Asaas', 'Bradesco', 'Sicoob1', 'Sicoob2', 'Sicoob3', 
                                          'Stone', 'Itaú4', 'Banco do Brasil1', 'Safra', 
                                          'Santander2', 'Efi1', 'Efi2', 'Mercado Pago']:
                        file.seek(0)
                        text = read_pdf2(file)
                    
                    processor = get_processor(identified_bank)
                    xml_data, txt_data = processor(text)
                    
                    if xml_data is None or txt_data is None:
                        self.log_message(f"Nenhuma transação encontrada", "error")
                        failed += 1
                        continue
                    
                    xml_data.seek(0)
                    csv_data = xml_to_csv(xml_data)
                    
                    output_filename = self.renomeador.gerar_nome_arquivo(
                        text,
                        identified_bank,
                        pdf_file.stem,
                        incluir_banco=True
                    )
                    self.log_message(f"Nome gerado: {output_filename}", "info")
                    
                    output_path = output_folder / output_filename
                    
                    with open(output_path, 'wb') as output_file:
                        output_file.write(csv_data.getvalue())
                    
                    self.log_message(f"Salvo em: {output_path}", "success")
                    successful += 1
                    
            except Exception as e:
                self.log_message(f"Erro: {str(e)}", "error")
                failed += 1
            
            self.progress_bar['value'] = index
            self.progress_label.config(text=f"{index} / {total_files} arquivos processados")
            
        # Finalizar
        self.log_message("=" * 60, "info")
        self.log_message(f"Processamento concluído!", "info")
        self.log_message(f"Sucesso: {successful} arquivo(s)", "success")
        if failed > 0:
            self.log_message(f"Falha: {failed} arquivo(s)", "error")
        
        self.process_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.is_processing = False
        
        messagebox.showinfo("Concluído", 
                          f"Processamento concluído!\n\n"
                          f"Sucesso: {successful}\n"
                          f"Falha: {failed}")


def main():
    root = tk.Tk()
    app = BatchProcessorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()