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
        self.root.geometry("900x600")
        self.root.resizable(True, True)
        
        self.input_folder = None
        self.output_folder = None
        self.is_processing = False
        self.renomeador = RenomeadorExtrato()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface do usuário"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Pasta de entrada
        ttk.Label(main_frame, text="Pasta de Entrada:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_entry = ttk.Entry(main_frame, width=50)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(main_frame, text="Selecionar", command=self.select_input_folder).grid(row=0, column=2, pady=5)
        
        # Pasta de saída
        ttk.Label(main_frame, text="Pasta de Saída:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_entry = ttk.Entry(main_frame, width=50)
        self.output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(main_frame, text="Selecionar", command=self.select_output_folder).grid(row=1, column=2, pady=5)
        
        # Frame de botões
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.process_btn = ttk.Button(button_frame, text="Processar", command=self.start_processing)
        self.process_btn.grid(row=0, column=0, padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancelar", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_btn.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Limpar Log", command=self.clear_log).grid(row=0, column=2, padx=5)
        
        # Barra de progresso
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0 / 0 arquivos processados")
        self.progress_label.grid(row=1, column=0, pady=2)
        
        # Área de log
        log_frame = ttk.LabelFrame(main_frame, text="Log de Processamento", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Text widget com scrollbar
        self.log_text = tk.Text(log_frame, height=20, width=80, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Tags para colorir o log
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("warning", foreground="orange")
        
    def select_input_folder(self):
        """Seleciona a pasta de entrada"""
        folder = filedialog.askdirectory(title="Selecione a pasta com os PDFs")
        if folder:
            self.input_folder = folder
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, folder)
            self.log_message(f"Pasta de entrada selecionada: {folder}", "info")
            
    def select_output_folder(self):
        """Seleciona a pasta de saída"""
        folder = filedialog.askdirectory(title="Selecione a pasta de saída")
        if folder:
            self.output_folder = folder
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            self.log_message(f"Pasta de saída selecionada: {folder}", "info")
            
    def log_message(self, message, tag="info"):
        """Adiciona uma mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        """Limpa o log"""
        self.log_text.delete(1.0, tk.END)
        
    def start_processing(self):
        """Inicia o processamento em lote"""
        if not self.input_folder or not self.output_folder:
            messagebox.showerror("Erro", "Selecione as pastas de entrada e saída!")
            return
            
        if not os.path.exists(self.input_folder):
            messagebox.showerror("Erro", "A pasta de entrada não existe!")
            return
            
        # Criar pasta de saída se não existir
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Buscar todos os PDFs
        pdf_files = list(Path(self.input_folder).glob("*.pdf"))
        
        if not pdf_files:
            messagebox.showwarning("Aviso", "Nenhum arquivo PDF encontrado na pasta de entrada!")
            return
            
        self.log_message(f"Encontrados {len(pdf_files)} arquivos PDF", "info")
        self.log_message("="*60, "info")
        
        # Desabilitar botão de processar e habilitar cancelar
        self.process_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.is_processing = True
        
        # Iniciar processamento em thread separada
        thread = threading.Thread(target=self.process_files, args=(pdf_files,), daemon=True)
        thread.start()
        
    def cancel_processing(self):
        """Cancela o processamento"""
        self.is_processing = False
        self.log_message("Processamento cancelado pelo usuário", "warning")
        self.process_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        
    def process_files(self, pdf_files):
        """Processa todos os arquivos PDF"""
        total_files = len(pdf_files)
        successful = 0
        failed = 0
        
        self.progress_bar['maximum'] = total_files
        self.progress_bar['value'] = 0
        
        for index, pdf_file in enumerate(pdf_files, 1):
            if not self.is_processing:
                break
                
            self.log_message(f"\n[{index}/{total_files}] Processando: {pdf_file.name}", "info")
            
            try:
                # Abrir arquivo
                with open(pdf_file, 'rb') as file:
                    # Identificar banco
                    text, identified_bank = read_pdf(file)
                    
                    if not text or identified_bank.startswith("Erro") or identified_bank == "Banco não identificado":
                        self.log_message(f"❌ {pdf_file.name}: Banco não identificado", "error")
                        failed += 1
                        continue
                    
                    self.log_message(f"   Banco identificado: {identified_bank}", "info")
                    
                    # Usar read_pdf2 para bancos específicos
                    if identified_bank in ['Asaas', 'Bradesco', 'Sicoob1', 'Sicoob2', 'Sicoob3', 
                                          'Stone', 'Itaú4', 'Banco do Brasil1', 'Safra', 
                                          'Santander2', 'Efi1', 'Efi2', 'Mercado Pago']:
                        file.seek(0)
                        text = read_pdf2(file)
                    
                    # Processar
                    processor = get_processor(identified_bank)
                    xml_data, txt_data = processor(text)
                    
                    if xml_data is None or txt_data is None:
                        self.log_message(f"❌ {pdf_file.name}: Nenhuma transação encontrada", "error")
                        failed += 1
                        continue
                    
                    # Converter para CSV
                    xml_data.seek(0)
                    csv_data = xml_to_csv(xml_data)
                    
                    # Gerar nome do arquivo (sempre com renomeação)
                    output_filename = self.renomeador.gerar_nome_arquivo(
                        text, 
                        identified_bank, 
                        pdf_file.stem
                    )
                    self.log_message(f"   Nome gerado: {output_filename}", "info")
                    
                    output_path = Path(self.output_folder) / output_filename
                    
                    # Salvar arquivo
                    with open(output_path, 'wb') as output_file:
                        output_file.write(csv_data.getvalue())
                    
                    self.log_message(f"✅ {pdf_file.name}: Processado com sucesso → {output_filename}", "success")
                    successful += 1
                    
            except Exception as e:
                self.log_message(f"❌ {pdf_file.name}: Erro - {str(e)}", "error")
                failed += 1
            
            # Atualizar progresso
            self.progress_bar['value'] = index
            self.progress_label.config(text=f"{index} / {total_files} arquivos processados")
            
        # Finalizar
        self.log_message("="*60, "info")
        self.log_message(f"Processamento concluído!", "info")
        self.log_message(f"✅ Sucesso: {successful} arquivo(s)", "success")
        if failed > 0:
            self.log_message(f"❌ Falha: {failed} arquivo(s)", "error")
        
        self.process_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.is_processing = False
        
        # Mostrar mensagem final
        messagebox.showinfo("Concluído", 
                          f"Processamento concluído!\n\n"
                          f"Sucesso: {successful}\n"
                          f"Falha: {failed}\n\n"
                          f"Arquivos salvos em:\n{self.output_folder}")


def main():
    """Função principal para executar a aplicação"""
    root = tk.Tk()
    app = BatchProcessorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()