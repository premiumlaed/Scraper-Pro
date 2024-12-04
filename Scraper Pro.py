import customtkinter as ctk
from tkinter import messagebox
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
import json
import re
from typing import Dict, List, Tuple
import threading
from datetime import datetime
import random
import os
from webdriver_manager.chrome import ChromeDriverManager

# تعيين مظهر التطبيق
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class DataExtractor:
    """فئة استخراج البيانات"""

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, text)
        cleaned_emails = [email.lower() for email in emails if len(email) > 5]
        return list(set(cleaned_emails))

    @staticmethod
    def extract_phones(text: str) -> List[str]:
        phone_patterns = [
            r'\+\d{1,4}[-\s]?\d{1,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',
            r'$\d{3}$[-\s]?\d{3}[-\s]?\d{4}',
            r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',
            r'00\d{1,3}[-\s]?\d{1,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',
            r'(?:971|0)?(?:2|3|4|6|7|9|50|51|52|55|56|58)\d{7}',
            r'(?:966|0)?(?:5|8|9)\d{8}'
        ]

        phones = []
        for pattern in phone_patterns:
            found = re.findall(pattern, text)
            phones.extend(found)

        cleaned_phones = []
        for phone in phones:
            cleaned = re.sub(r'[\s\(\)-]', '', phone)
            if len(cleaned) >= 8:
                cleaned_phones.append(cleaned)

        return list(set(cleaned_phones))

    @staticmethod
    def clean_text(text: str) -> str:
        return re.sub(r'[^\w\s@+\(\)\-\.]', '', text)

    @staticmethod
    def extract_contact_info(text: str) -> Tuple[List[str], List[str]]:
        cleaned_text = DataExtractor.clean_text(text)
        emails = DataExtractor.extract_emails(cleaned_text)
        phones = DataExtractor.extract_phones(cleaned_text)
        return emails, phones

class GoogleScraper:
    """فئة التعامل مع Google"""

    def __init__(self):
        self.options = Options()
        self.setup_options()
        self.driver = None

    def setup_options(self):
        """إعداد خيارات المتصفح"""
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-notifications')
        self.options.add_argument('--start-maximized')
        self.options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    def initialize_driver(self):
        """تهيئة المتصفح"""
        try:
            if not self.driver:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=self.options)
            return self.driver
        except Exception as e:
            print(f"Error initializing driver: {str(e)}")
            raise

    def close_driver(self):
        """إغلاق المتصفح"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            print(f"Error closing driver: {str(e)}")

    def search_google(self, query: str):
        """البحث في Google"""
        try:
            self.driver.get(f"https://www.google.com/search?q={query}")
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"Search error: {str(e)}")
            raise

    def get_search_results(self):
        """استخراج نتائج البحث"""
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, "div.g")
        except Exception as e:
            print(f"Error getting results: {str(e)}")
            return []

    def scroll_page(self):
        """التمرير في الصفحة"""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(1, 2))
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception as e:
            print(f"Scroll error: {str(e)}")

    def next_page(self):
        """الانتقال للصفحة التالية"""
        try:
            next_button = self.driver.find_element(By.ID, "pnnext")
            next_button.click()
            time.sleep(random.uniform(2, 4))
            return True
        except:
            return False
class ScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # إعداد النافذة الرئيسية
        self.title("Google Scraper Pro")
        self.geometry("1200x800")

        # إعداد المتغيرات
        self.scraper = GoogleScraper()
        self.results = []
        self.stop_search_flag = False

        # إعداد الواجهة
        self.setup_ui()

        # تعيين النمط
        self.configure(fg_color=("white", "gray10"))

    def setup_ui(self):
        """إعداد واجهة المستخدم"""
        # إعداد الشبكة الرئيسية
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # إطار البحث
        self.create_search_frame()

        # إطار الإعدادات المتقدمة
        self.create_advanced_frame()

        # إطار النتائج
        self.create_results_frame()

    def create_search_frame(self):
        """إنشاء إطار البحث"""
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # عنوان الوظيفة
        ctk.CTkLabel(search_frame, text="Job Title:").grid(row=0, column=0, padx=5, pady=5)
        self.job_title = ctk.CTkEntry(search_frame, width=300, placeholder_text="Enter job title...")
        self.job_title.grid(row=0, column=1, padx=5, pady=5)

        # الشركة
        ctk.CTkLabel(search_frame, text="Company:").grid(row=1, column=0, padx=5, pady=5)
        self.company = ctk.CTkEntry(search_frame, width=300, placeholder_text="Enter company name or * for all")
        self.company.grid(row=1, column=1, padx=5, pady=5)

        # الموقع
        ctk.CTkLabel(search_frame, text="Location:").grid(row=2, column=0, padx=5, pady=5)
        self.location = ctk.CTkEntry(search_frame, width=300, placeholder_text="Enter location...")
        self.location.grid(row=2, column=1, padx=5, pady=5)

    def create_advanced_frame(self):
        """إنشاء إطار الإعدادات المتقدمة"""
        advanced_frame = ctk.CTkFrame(self)
        advanced_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # المنصة
        ctk.CTkLabel(advanced_frame, text="Platform:").grid(row=0, column=0, padx=5, pady=5)
        self.platform = ctk.CTkComboBox(
            advanced_frame,
            values=["LinkedIn", "Facebook", "All"],
            width=200
        )
        self.platform.grid(row=0, column=1, padx=5, pady=5)
        self.platform.set("LinkedIn")

        # عدد الصفحات
        ctk.CTkLabel(advanced_frame, text="Max Pages:").grid(row=0, column=2, padx=5, pady=5)
        self.max_pages = ctk.CTkEntry(advanced_frame, width=100)
        self.max_pages.grid(row=0, column=3, padx=5, pady=5)
        self.max_pages.insert(0, "10")

        # شريط التقدم
        self.progress = ctk.CTkProgressBar(advanced_frame)
        self.progress.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.progress.set(0)

        # حالة البحث
        self.status_label = ctk.CTkLabel(advanced_frame, text="Ready")
        self.status_label.grid(row=2, column=0, columnspan=4, pady=5)

        # أزرار التحكم
        button_frame = ctk.CTkFrame(advanced_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=5)

        self.search_button = ctk.CTkButton(
            button_frame,
            text="Start Search",
            command=self.start_search,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.search_button.pack(side="left", padx=5)

        self.stop_button = ctk.CTkButton(
            button_frame,
            text="Stop",
            command=self.stop_search,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)

    def create_results_frame(self):
        """إنشاء إطار النتائج"""
        results_frame = ctk.CTkFrame(self)
        results_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        # إنشاء إطار قابل للتمرير للنتائج
        self.results_canvas = ctk.CTkScrollableFrame(results_frame)
        self.results_canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # أزرار التصدير
        export_frame = ctk.CTkFrame(results_frame)
        export_frame.grid(row=1, column=0, pady=5)

        ctk.CTkButton(
            export_frame,
            text="Export to CSV",
            command=self.export_csv,
            fg_color="blue",
            hover_color="darkblue"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            export_frame,
            text="Export to JSON",
            command=self.export_json,
            fg_color="purple",
            hover_color="darkpurple"
        ).pack(side="left", padx=5)
    def add_result_to_table(self, title, company, location, emails, phones, url, platform):
        """إضافة نتيجة إلى الجدول"""
        result_frame = ctk.CTkFrame(self.results_canvas)
        result_frame.pack(fill="x", padx=5, pady=2)

        # إطار المعلومات الأساسية
        info_frame = ctk.CTkFrame(result_frame)
        info_frame.pack(side="left", fill="x", expand=True, padx=5)

        # العنوان
        title_label = ctk.CTkLabel(
            info_frame,
            text=title,
            wraplength=300,
            justify="left",
            font=("Arial", 12, "bold"),
            text_color=("blue", "lightblue")
        )
        title_label.pack(anchor="w", pady=2)

        # معلومات الشركة والموقع
        company_location = f"🏢 {company} | 📍 {location}"
        ctk.CTkLabel(
            info_frame,
            text=company_location,
            font=("Arial", 10),
            text_color=("gray40", "gray60")
        ).pack(anchor="w")

        # معلومات الاتصال
        if emails:
            email_text = "📧 " + ", ".join(emails)
            ctk.CTkLabel(
                info_frame,
                text=email_text,
                font=("Arial", 10),
                text_color=("green", "lightgreen")
            ).pack(anchor="w")

        if phones:
            phone_text = "📱 " + ", ".join(phones)
            ctk.CTkLabel(
                info_frame,
                text=phone_text,
                font=("Arial", 10),
                text_color=("orange", "yellow")
            ).pack(anchor="w")

        # إطار الأزرار
        button_frame = ctk.CTkFrame(result_frame)
        button_frame.pack(side="right", padx=5)

        # زر فتح الرابط
        ctk.CTkButton(
            button_frame,
            text="🌐 Open URL",
            command=lambda: self.open_url(url),
            width=100,
            height=32,
            fg_color=("blue", "darkblue"),
            hover_color=("navy", "navy")
        ).pack(side="top", pady=2)

        # زر نسخ المعلومات
        ctk.CTkButton(
            button_frame,
            text="📋 Copy Info",
            command=lambda: self.copy_info(title, company, location, emails, phones, url),
            width=100,
            height=32,
            fg_color=("green", "darkgreen"),
            hover_color=("darkgreen", "darkgreen")
        ).pack(side="top", pady=2)

    def scrape_results(self, query: str):
        """وظيفة الكشط الرئيسية"""
        try:
            # تهيئة المتصفح
            if not self.scraper.driver:
                self.update_status("Initializing browser...")
                self.scraper.initialize_driver()

            # البحث في Google
            self.update_status("Starting search...")
            self.scraper.search_google(query)

            total_results = 0
            max_pages = int(self.max_pages.get())
            data_extractor = DataExtractor()

            for page in range(max_pages):
                if self.stop_search_flag:
                    break

                self.update_status(f"Scraping page {page + 1} of {max_pages}")
                self.progress.set((page + 1) / max_pages)

                # التمرير في الصفحة
                self.scraper.scroll_page()

                # استخراج النتائج
                results = self.scraper.get_search_results()

                if not results:
                    self.update_status("No results found on this page")
                    break

                for result in results:
                    if self.stop_search_flag:
                        break

                    try:
                        # استخراج البيانات
                        title = result.find_element(By.CSS_SELECTOR, "h3").text
                        link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")

                        try:
                            snippet = result.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                        except:
                            snippet = ""

                        # استخراج معلومات الاتصال
                        emails, phones = data_extractor.extract_contact_info(snippet)

                        # إضافة النتيجة
                        self.add_result_to_table(
                            title,
                            self.company.get() if self.company.get() else "Any",
                            self.location.get(),
                            emails,
                            phones,
                            link,
                            self.platform.get()
                        )

                        # حفظ النتيجة
                        self.results.append({
                            'title': title,
                            'company': self.company.get() if self.company.get() else "Any",
                            'location': self.location.get(),
                            'emails': emails,
                            'phones': phones,
                            'url': link,
                            'platform': self.platform.get(),
                            'snippet': snippet
                        })

                        total_results += 1

                    except Exception as e:
                        print(f"Error processing result: {str(e)}")
                        continue

                # الانتقال للصفحة التالية
                if not self.scraper.next_page():
                    self.update_status("Reached last page")
                    break

            final_message = f"Completed! Found {total_results} results"
            self.update_status(final_message)

            if total_results == 0:
                messagebox.showinfo("Search Complete", "No results found matching your criteria")

        except Exception as e:
            error_message = f"Scraping error: {str(e)}"
            print(error_message)
            messagebox.showerror("Error", error_message)
            self.update_status("Search failed")
        finally:
            self.search_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.progress.set(0)

    def start_search(self):
        """بدء عملية البحث"""
        if not self.job_title.get():
            messagebox.showerror("Error", "Please enter a job title")
            return

        self.search_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.results = []
        self.clear_results_display()

        # بناء استعلام البحث
        query = self.build_search_query()

        # بدء البحث في thread منفصل
        threading.Thread(target=self.scrape_results, args=(query,), daemon=True).start()

    def build_search_query(self) -> str:
        """بناء استعلام البحث"""
        query_parts = []

        if self.platform.get() != "All":
            query_parts.append(f'site:{self.platform.get().lower()}.com')

        query_parts.append(f'"{self.job_title.get()}"')

        if self.company.get() and self.company.get() != "*":
            query_parts.append(f'"{self.company.get()}"')

        if self.location.get():
            query_parts.append(f'"{self.location.get()}"')

        query_parts.append('"email" OR "contact" OR "phone" OR "mobile"')

        return " ".join(query_parts)

    def stop_search(self):
        """إيقاف عملية البحث"""
        self.stop_search_flag = True
        self.update_status("Stopping search...")
        self.stop_button.configure(state="disabled")

    def clear_results_display(self):
        """مسح النتائج السابقة"""
        for widget in self.results_canvas.winfo_children():
            widget.destroy()

    def update_status(self, message: str):
        """تحديث حالة البحث"""
        self.status_label.configure(text=message)
        self.update()

    def open_url(self, url: str):
        """فتح الرابط في المتصفح"""
        import webbrowser
        webbrowser.open(url)

    def copy_info(self, title, company, location, emails, phones, url):
        """نسخ معلومات النتيجة"""
        info = f"""
Title: {title}
Company: {company}
Location: {location}
Emails: {', '.join(emails) if emails else 'None'}
Phones: {', '.join(phones) if phones else 'None'}
URL: {url}
        """
        self.clipboard_clear()
        self.clipboard_append(info)
        self.show_toast("Information copied to clipboard!")

    def show_toast(self, message, duration=2000):
        """إظهار رسالة تأكيد مؤقتة"""
        toast = ctk.CTkFrame(self)
        toast.place(relx=0.5, rely=0.9, anchor="center")

        ctk.CTkLabel(
            toast,
            text=message,
            font=("Arial", 12),
            text_color=("green", "lightgreen")
        ).pack(padx=20, pady=10)

        self.after(duration, toast.destroy)

    def export_csv(self):
        """تصدير النتائج إلى CSV"""
        if not self.results:
            messagebox.showwarning("Warning", "No data to export")
            return

        try:
            filename = f"google_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            data = []
            for result in self.results:
                data.append({
                    'Title': result['title'],
                    'Company': result['company'],
                    'Location': result['location'],
                    'Emails': ', '.join(result['emails']),
                    'Phones': ', '.join(result['phones']),
                    'URL': result['url'],
                    'Platform': result['platform']
                })

            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            messagebox.showinfo("Success", f"Data exported to {filename}")

            os.startfile(os.path.dirname(os.path.abspath(filename)))

        except Exception as e:
            messagebox.showerror("Error", f"Export error: {str(e)}")

    def export_json(self):
        """تصدير النتائج إلى JSON"""
        if not self.results:
            messagebox.showwarning("Warning", "No data to export")
            return

        try:
            filename = f"google_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(filename, "w", encoding='utf-8') as f:
                json.dump(self.results, f, indent=4, ensure_ascii=False)

            messagebox.showinfo("Success", f"Data exported to {filename}")

            os.startfile(os.path.dirname(os.path.abspath(filename)))

        except Exception as e:
            messagebox.showerror("Error", f"Export error: {str(e)}")

    def on_closing(self):
        """معالجة إغلاق التطبيق"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.scraper:
                self.scraper.close_driver()
            self.quit()

if __name__ == "__main__":
    try:
        app = ScraperApp()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        print(f"Application error: {str(e)}")
