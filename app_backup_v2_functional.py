import os
import sys
import json
import time
import wave
import threading
import queue
from datetime import datetime
from pathlib import Path
import pyaudio
import keyboard
from faster_whisper import WhisperModel
from colorama import init, Fore, Style

# Initialiser colorama pour les couleurs dans le terminal
init()

# CORRECTION: Désactiver les symlinks pour éviter l'erreur de privilèges Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

import tempfile
import threading
import wave
import pyaudio
import keyboard
import pyautogui
import tkinter as tk
from tkinter import ttk, Canvas
import time
import pyperclip
from faster_whisper import WhisperModel

class VoiceTranscriptionApp:
    def __init__(self):
        # Configuration audio
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.recording = False
        self.audio_data = []
        self.running = True
        self.microphone_name = "TONOR TD510 Dynamic Mic"
        self.microphone_index = None

        # Buffer pour la dernière transcription
        self.last_transcription = ""

        # Queue pour l'indicateur de transcription
        self.transcription_queue = queue.Queue()
        self.transcription_indicator_window = None
        
        # Initiali
        # sation PyAudio
        self.audio = pyaudio.PyAudio()
        
        # Trouver le microphone spécifique
        self._find_microphone()
        
        # Détection automatique du GPU
        device = "cuda" if self._check_gpu() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"Initialisation du modèle Whisper large-v3 sur {device} avec compute_type {compute_type}")
        
        # Initialisation du modèle Whisper large-v3 comme demandé
        self.model = WhisperModel(
            "large-v3",  # Modèle large-v3 comme spécifié
            device=device,
            compute_type=compute_type,
            cpu_threads=4 if device == "cpu" else 4
        )
        
        # Configuration des raccourcis clavier
        keyboard.add_hotkey('ctrl+f9', self.toggle_recording)
        keyboard.add_hotkey('ctrl+shift+f9', self.reinject_last_transcription)
        keyboard.add_hotkey('ctrl+f10', self.quit_app)

        # Indicateur visuel d'enregistrement
        self.indicator_window = None
        self.indicator_thread = None

        print("Application prête !")
        print("Appuyez sur Ctrl+F9 pour commencer/arrêter l'enregistrement")
        print("Appuyez sur Ctrl+Shift+F9 pour réinjecter la dernière transcription")
        print("Appuyez sur Ctrl+F10 pour quitter")
        if self.microphone_index is not None:
            print(f"Microphone sélectionné: {self.microphone_name}")
        else:
            print("Attention: Microphone TONOR TD510 Dynamic Mic non trouvé, utilisation du microphone par défaut")

        # Afficher l'indicateur "modèle chargé"
        self.show_ready_indicator()
    
    def _check_gpu(self):
        """Vérifie la disponibilité du GPU CUDA"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            # Vérification alternative sans torch
            try:
                import ctranslate2
                return ctranslate2.get_cuda_device_count() > 0
            except:
                return False
    
    def _find_microphone(self):
        """Trouve l'index du microphone TONOR TD510 Dynamic Mic"""
        print("Recherche du microphone TONOR TD510 Dynamic Mic...")
        
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            device_name = device_info.get('name', '')
            
            # Vérifier si c'est un périphérique d'entrée
            if device_info.get('maxInputChannels', 0) > 0:
                print(f"Microphone trouvé: {device_name} (index: {i})")
                
                # Recherche du microphone TONOR (recherche flexible)
                if "tonor" in device_name.lower() or "td510" in device_name.lower():
                    self.microphone_index = i
                    print(f"✅ Microphone TONOR trouvé à l'index {i}")
                    return
        
        print("⚠️ Microphone TONOR TD510 Dynamic Mic non trouvé, utilisation du microphone par défaut")
    
    def toggle_recording(self):
        """Démarre ou arrête l'enregistrement"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Démarre l'enregistrement audio"""
        if self.recording:
            return
        
        print("🎤 Début de l'enregistrement...")
        self.recording = True
        self.audio_data = []
        self.show_recording_indicator()
        
        # Configuration du stream audio avec le microphone spécifique
        try:
            stream_kwargs = {
                'format': self.format,
                'channels': self.channels,
                'rate': self.rate,
                'input': True,
                'frames_per_buffer': self.chunk
            }
            
            # Utiliser le microphone spécifique s'il est trouvé
            if self.microphone_index is not None:
                stream_kwargs['input_device_index'] = self.microphone_index
            
            self.stream = self.audio.open(**stream_kwargs)
            
            # Thread pour l'enregistrement
            self.record_thread = threading.Thread(target=self._record_audio)
            self.record_thread.start()
            
        except Exception as e:
            print(f"Erreur lors de l'ouverture du stream audio: {e}")
            self.recording = False
    
    def _record_audio(self):
        """Enregistre l'audio en continu"""
        while self.recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.audio_data.append(data)
            except Exception as e:
                print(f"Erreur lors de l'enregistrement: {e}")
                break
    
    def stop_recording(self):
        """Arrête l'enregistrement et transcrit"""
        if not self.recording:
            return
        
        print("⏹️ Arrêt de l'enregistrement...")
        self.recording = False
        self.hide_recording_indicator()
        
        # Attendre la fin du thread d'enregistrement
        if hasattr(self, 'record_thread'):
            self.record_thread.join()
        
        # Fermer le stream
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        
        # Sauvegarder et transcrire
        if self.audio_data:
            self.save_and_transcribe()
    
    def show_transcription_indicator(self):
        """Affiche l'indicateur de progression de transcription"""
        def create_transcription_indicator():
            try:
                indicator = tk.Tk()
                indicator.title("Transcription")
                indicator.configure(bg='#3b82f6')  # Bleu moderne
                indicator.overrideredirect(True)
                indicator.attributes('-topmost', True)
                indicator.attributes('-alpha', 0.95)

                # Positionner en haut à droite (sous l'indicateur REC)
                indicator.update_idletasks()
                screen_width = indicator.winfo_screenwidth()
                win_width = 350
                win_height = 100
                x_pos = screen_width - win_width - 20
                y_pos = 80  # En dessous de l'indicateur REC qui est à y=20
                indicator.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")

                # Label pour le statut (segment X)
                status_label = tk.Label(indicator, text="⏳ Transcription...",
                                      bg='#3b82f6', fg='white',
                                      font=('Segoe UI', 12, 'bold'))
                status_label.pack(pady=(10, 5))

                # Label pour le texte transcrit (derniers caractères)
                text_label = tk.Label(indicator, text="",
                                    bg='#3b82f6', fg='white',
                                    font=('Segoe UI', 9),
                                    wraplength=330,
                                    justify='left')
                text_label.pack(pady=(0, 10), padx=10)

                # Stocker la référence
                self.transcription_indicator_window = indicator

                # Fonction pour mettre à jour l'indicateur depuis la queue
                def update_from_queue():
                    try:
                        # Lire tous les messages disponibles dans la queue
                        while True:
                            msg_type, msg_data = self.transcription_queue.get_nowait()

                            if msg_type == "segment":
                                current_seg, text = msg_data
                                status_label.config(text=f"⏳ Transcription... (segment {current_seg})")
                                # Afficher les 120 derniers caractères
                                display_text = text[-120:] if len(text) > 120 else text
                                text_label.config(text=display_text)

                            elif msg_type == "done":
                                status_label.config(text="✓ Transcription terminée")
                                text_label.config(text="Injection du texte...")
                                # Fermer après 2 secondes
                                indicator.after(2000, lambda: self._close_transcription_indicator(indicator))
                                return

                            elif msg_type == "error":
                                status_label.config(text="❌ Erreur")
                                text_label.config(text=str(msg_data))
                                indicator.after(3000, lambda: self._close_transcription_indicator(indicator))
                                return

                    except queue.Empty:
                        pass

                    # Continuer à vérifier la queue toutes les 100ms
                    if self.transcription_indicator_window:
                        indicator.after(100, update_from_queue)

                # Démarrer la vérification de la queue
                update_from_queue()

                # Maintenir la fenêtre ouverte
                indicator.mainloop()

            except Exception as e:
                print(f"Erreur création indicateur transcription: {e}")

        # Lancer l'indicateur dans un thread séparé
        indicator_thread = threading.Thread(target=create_transcription_indicator, daemon=True)
        indicator_thread.start()
        time.sleep(0.15)  # Laisser le temps à la fenêtre de se créer

    def _close_transcription_indicator(self, indicator):
        """Ferme l'indicateur de transcription"""
        try:
            if indicator:
                indicator.quit()
                indicator.destroy()
                self.transcription_indicator_window = None
        except Exception as e:
            print(f"Erreur fermeture indicateur transcription: {e}")

    def save_and_transcribe(self):
        """Sauvegarde l'audio et effectue la transcription"""
        # Afficher l'indicateur de progression
        self.show_transcription_indicator()

        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name

            # Sauvegarder l'audio
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.audio_data))

        print("🔄 Transcription en cours avec le modèle large-v3...")

        try:
            # Transcription avec faster-whisper selon les bonnes pratiques
            segments, info = self.model.transcribe(
                temp_filename,
                language=None,  # Détection automatique de la langue
                task="transcribe",
                vad_filter=True,  # Filtrage de l'activité vocale
                vad_parameters={"min_silence_duration_ms": 500},
                word_timestamps=False,
                beam_size=5,
                best_of=5,
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6,
                condition_on_previous_text=True
            )

            # Récupérer le texte transcrit avec mise à jour progressive
            # NE PAS convertir en liste pour éviter de bloquer sur de longs audios
            transcription = ""
            segment_count = 0
            for segment in segments:
                segment_count += 1
                transcription += segment.text
                # Envoyer une mise à jour à l'indicateur (sans total pour éviter le blocage)
                self.transcription_queue.put(("segment", (segment_count, transcription)))

            transcription = transcription.strip()

            if transcription:
                print(f"✅ Transcription ({info.language}): {transcription}")
                # Sauvegarder dans le buffer avant d'injecter
                self.last_transcription = transcription
                # Signaler que la transcription est terminée
                self.transcription_queue.put(("done", None))
                # Insérer le texte à la position du curseur avec support des accents
                self.insert_text_with_accents(transcription)
            else:
                print("❌ Aucune parole détectée")
                self.transcription_queue.put(("error", "Aucune parole détectée"))

        except Exception as e:
            print(f"Erreur lors de la transcription: {e}")
            self.transcription_queue.put(("error", str(e)))

        finally:
            # Nettoyer le fichier temporaire
            try:
                os.unlink(temp_filename)
            except:
                pass
    
    def reinject_last_transcription(self):
        """Réinjecte la dernière transcription au curseur"""
        if self.last_transcription:
            print(f"📋 Réinjection de la dernière transcription: {self.last_transcription}")
            self.insert_text_with_accents(self.last_transcription)
        else:
            print("⚠️ Aucune transcription dans le buffer")

    def insert_text_with_accents(self, text):
        """Insère du texte avec support des caractères accentués"""
        try:
            # Méthode 1: Utiliser le presse-papiers (plus fiable pour les accents)
            # Sauvegarder le contenu actuel du presse-papiers
            try:
                original_clipboard = pyperclip.paste()
            except:
                original_clipboard = ""
            
            # Copier le texte transcrit dans le presse-papiers
            pyperclip.copy(text)
            
            # Petit délai pour s'assurer que le presse-papiers est mis à jour
            time.sleep(0.1)
            
            # Coller le texte avec Ctrl+V
            pyautogui.hotkey('ctrl', 'v')
            
            # Petit délai avant de restaurer le presse-papiers
            time.sleep(0.2)
            
            # Restaurer le contenu original du presse-papiers
            try:
                pyperclip.copy(original_clipboard)
            except:
                pass
                
        except Exception as e:
            print(f"Erreur lors de l'insertion du texte: {e}")
            # Fallback: essayer avec pyautogui (sans accents)
            try:
                # Remplacer les caractères accentués par leurs équivalents
                text_fallback = (text.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
                               .replace('à', 'a').replace('â', 'a').replace('ä', 'a')
                               .replace('ù', 'u').replace('û', 'u').replace('ü', 'u')
                               .replace('ô', 'o').replace('ö', 'o').replace('ò', 'o')
                               .replace('î', 'i').replace('ï', 'i').replace('ì', 'i')
                               .replace('ç', 'c').replace('ñ', 'n')
                               .replace('É', 'E').replace('È', 'E').replace('Ê', 'E')
                               .replace('À', 'A').replace('Â', 'A').replace('Ä', 'A')
                               .replace('Ù', 'U').replace('Û', 'U').replace('Ü', 'U')
                               .replace('Ô', 'O').replace('Ö', 'O').replace('Ò', 'O')
                               .replace('Î', 'I').replace('Ï', 'I').replace('Ì', 'I')
                               .replace('Ç', 'C').replace('Ñ', 'N'))
                pyautogui.typewrite(text_fallback)
                print("⚠️ Texte inséré sans accents (fallback)")
            except:
                print("❌ Impossible d'insérer le texte")
    
    def show_ready_indicator(self):
        """Affiche l'indicateur 'modèle chargé' en bas à droite"""
        def create_ready_indicator():
            try:
                indicator = tk.Tk()
                indicator.title("Ready")
                indicator.configure(bg='#10b981')  # Vert moderne
                indicator.overrideredirect(True)
                indicator.attributes('-topmost', True)
                indicator.attributes('-alpha', 0.95)

                # Positionner en haut à droite
                indicator.update_idletasks()
                screen_width = indicator.winfo_screenwidth()
                indicator.geometry(f"180x60+{screen_width-200}+20")

                # Label avec icône et texte
                label = tk.Label(indicator, text="✓ Whisper Ready",
                               bg='#10b981', fg='white',
                               font=('Segoe UI', 14, 'bold'))
                label.pack(expand=True)

                # Fermer automatiquement après 3 secondes
                indicator.after(3000, indicator.destroy)

                indicator.mainloop()

            except Exception as e:
                print(f"Erreur création indicateur ready: {e}")

        # Lancer dans un thread séparé
        ready_thread = threading.Thread(target=create_ready_indicator, daemon=True)
        ready_thread.start()

    def show_recording_indicator(self):
        """Affiche l'indicateur d'enregistrement en haut à droite"""
        def create_indicator():
            try:
                # Créer une nouvelle fenêtre tkinter dans ce thread
                indicator = tk.Tk()
                indicator.title("REC")
                indicator.geometry("160x50")
                indicator.configure(bg='SystemButtonFace')  # Fond transparent
                indicator.overrideredirect(True)  # Pas de barre de titre
                indicator.attributes('-topmost', True)  # Toujours au premier plan
                indicator.attributes('-alpha', 0.95)  # Légèrement transparent

                # Positionner en haut à droite de l'écran
                indicator.update_idletasks()
                screen_width = indicator.winfo_screenwidth()
                indicator.geometry(f"160x50+{screen_width-180}+20")

                # Frame avec relief pour simuler coins arrondis
                frame = tk.Frame(indicator, bg='#dc2626', relief='flat', bd=0)
                frame.pack(expand=True, fill='both', padx=3, pady=3)

                # Label avec texte clignotant
                label = tk.Label(frame, text="● REC",
                               bg='#dc2626', fg='white',
                               font=('Segoe UI', 16, 'bold'),
                               bd=0, highlightthickness=0)
                label.pack(expand=True)

                # Stocker la référence
                self.indicator_window = indicator

                # Boucle pour faire clignoter
                def blink():
                    if self.recording and self.indicator_window:
                        try:
                            current_bg = '#991b1b' if label.cget('bg') == '#dc2626' else '#dc2626'
                            label.configure(bg=current_bg)
                            frame.configure(bg=current_bg)
                            indicator.after(500, blink)  # Clignoter toutes les 500ms
                        except:
                            pass

                # Démarrer le clignotement
                blink()

                # Maintenir la fenêtre ouverte
                indicator.mainloop()

            except Exception as e:
                print(f"Erreur création indicateur: {e}")

        # Lancer l'indicateur dans un thread séparé
        if self.indicator_thread is None or not self.indicator_thread.is_alive():
            self.indicator_thread = threading.Thread(target=create_indicator, daemon=True)
            self.indicator_thread.start()
            time.sleep(0.1)  # Petit délai pour laisser la fenêtre se créer
    
    def hide_recording_indicator(self):
        """Cache l'indicateur d'enregistrement"""
        try:
            if self.indicator_window:
                self.indicator_window.quit()
                self.indicator_window.destroy()
                self.indicator_window = None
        except Exception as e:
            print(f"Erreur fermeture indicateur: {e}")
    
    def quit_app(self):
        """Quitte l'application"""
        print("Fermeture de l'application...")
        self.running = False

    def run(self):
        """Lance l'application"""
        try:
            while self.running:
                keyboard.wait()
        except KeyboardInterrupt:
            print("\nInterruption par l'utilisateur")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Nettoie les ressources"""
        if self.recording:
            self.stop_recording()
        
        # Fermer l'indicateur
        self.hide_recording_indicator()
        
        if hasattr(self, 'audio'):
            self.audio.terminate()
        
        print("Ressources nettoyées")

if __name__ == "__main__":
    app = VoiceTranscriptionApp()
    app.run()