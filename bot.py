import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import re
import requests

from deobfuscator_core import Deobfuscator
from pattern_scanner import PatternScanner
from execution_engine import ExecutionEngine

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Slash komutlarını Discord'a kaydeder
        await self.tree.sync()
        print(f"Slash komutları senkronize edildi.")

bot = MyBot()

PASTEBIN_RE = re.compile(r'pastebin\.com/(?:raw/)?([a-zA-Z0-9]+)')
GITHUB_RE = re.compile(r'github\.com/([\w.-]+/[\w.-]+)/blob/([\w.-]+)/([\w./-]+)')

async def download_content(url):
    pb_match = PASTEBIN_RE.search(url)
    if pb_match:
        url = f"https://pastebin.com/raw/{pb_match.group(1)}"
    gh_match = GITHUB_RE.search(url)
    if gh_match:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    try:
        response = requests.get(url, timeout=10)
        return response.text if response.status_code == 200 else None
    except:
        return None

@bot.tree.command(name="deobfuscate", description="Lua dosyasını veya linkini analiz eder.")
@app_commands.describe(dosya="Analiz edilecek .lua veya .txt dosyası", link="Pastebin veya GitHub linki")
async def deobfuscate(interaction: discord.Interaction, dosya: discord.Attachment = None, link: str = None):
    await interaction.response.defer() # Botun düşünmesi için zaman kazanıyoruz

    content = ""
    filename = "analiz.lua"

    if dosya:
        if dosya.filename.endswith(('.lua', '.txt')):
            content = (await dosya.read()).decode('utf-8', errors='ignore')
            filename = dosya.filename
    elif link:
        content = await download_content(link)
        filename = "link_content.lua"

    if not content:
        await interaction.followup.send("❌ Lütfen geçerli bir dosya yükle veya link ver!")
        return

    temp_path = f"temp_{interaction.user.id}.lua"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        # Analiz Motorları
        deobf = Deobfuscator()
        string_results = deobf.analyze_script(temp_path)

        scanner = PatternScanner()
        scanner.load_default_patterns()
        pattern_results = scanner.analyze_target_file(temp_path)

        engine = ExecutionEngine(max_time=5)
        exec_results = engine.process_script_file(temp_path)

        # Rapor Oluşturma
        embed = discord.Embed(title="🛡️ Analiz Sonucu", color=discord.Color.blue())
        embed.add_field(name="Dosya", value=filename, inline=True)
        embed.add_field(name="Risk Skoru", value=f"{pattern_results.get('total_score_value', 0)} ({pattern_results.get('risk_assessment', 'Düşük')})", inline=True)
        embed.add_field(name="Çalıştırma Durumu", value="✅ Başarılı" if exec_results['execution_details']['successful'] else "❌ Başarısız", inline=False)
        
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"⚠️ Hata: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

bot.run('YOUR_TOKEN_HERE')
