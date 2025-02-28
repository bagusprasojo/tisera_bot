import mysql.connector
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.helpers import escape_markdown
from tabulate import tabulate

# Load .env file
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Ambil konfigurasi database dari .env
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

async def help_command(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    role = get_user_role(user_id)

    if not role:
        await update.message.reply_text("⛔ Anda belum terdaftar. Gunakan /login untuk masuk.")
        return

    help_text = (
        "📌 *Daftar Perintah yang Bisa Anda Akses:*\n\n"
        "/start - Mulai bot\n"
        "/order - Melihat daftar order\n"
    )

    if role == "Penyedia":
        help_text += "/profile - Lihat profil penyedia\n"
    elif role == "Super Admin":
        help_text += "/pembayaran - Kelola pembayaran\n"
        help_text += "/jumlah_order tahun bulan - Melihat jumlah order berdasarkan tahun dan bulan\n"
        help_text += "/nilai_order tahun bulan - Melihat nilai order berdasarkan tahun dan bulan\n"

    help_text += "\n/help - Melihat daftar perintah\n"

    # Escape markdown untuk menghindari error formatting
    await update.message.reply_text(escape_markdown(help_text, version=2), parse_mode="MarkdownV2")


def get_user_role(user_id):
    print(user_id)
    """
    Mengecek apakah user_id ada di view v_user_telegram.
    Jika ada, kembalikan role user. Jika tidak, kembalikan None.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query untuk mencari user berdasarkan id_telegram
        query = """
            SELECT role FROM v_user_telegram 
            WHERE id_telegram = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()

        return result[0] if result else None  # Kembalikan role jika ditemukan, jika tidak return None

    except Exception as e:
        print(f"Error saat mencari user: {str(e)}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Fungsi untuk membuat koneksi ke MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Fungsi untuk mengambil data jumlah order dari database
def get_data_order(tahun, bulan, jenis_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT DATE_FORMAT(tanggal, '%Y-%m-%d') AS tanggal, angka
            FROM v_cek_data_tisera
            WHERE hal = %s
            AND YEAR(tanggal) = %s
            AND MONTH(tanggal) = %s
            ORDER BY tanggal
        """
        cursor.execute(query, (jenis_data, tahun, bulan))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        if not results:
            return f"⚠️ Tidak ada data {jenis_data} untuk periode ini."

        # Format ulang jumlah order sebagai string dan rata kanan
        if jenis_data == "Jumlah Order" or jenis_data == "Jumlah Order Selesai":
            formatted_results = [(tgl, str(jumlah).zfill(4)) for tgl, jumlah in results]
        else:
            formatted_results = [(tgl, f"{jumlah:,}".rjust(15)) for tgl, jumlah in results]



        # Buat tabel dengan tabulate
        headers = ["Tanggal", "Jumlah"]
        table = tabulate(formatted_results, headers=headers, tablefmt="plain")

        return f"📊 *Jumlah Order - {bulan}/{tahun}*\n```\n{table}\n```"

    except Exception as e:
        return f"❌ Terjadi kesalahan: {e}"

async def handle_order(update: Update, context: CallbackContext, order_type: str, command_name: str) -> None:
    user_id = update.message.from_user.id
    role = get_user_role(user_id)

    # Cek apakah user memiliki role "Super Admin"
    if role != "Super Admin":
        await update.message.reply_text("⛔ Anda tidak memiliki akses ke fitur ini. Hanya *Super Admin* yang bisa mengakses.", parse_mode="Markdown")
        return

    # Periksa apakah parameter tahun dan bulan diberikan
    if len(context.args) < 2:
        await update.message.reply_text(
            f"⚠️ Format salah! Gunakan:\n`/{command_name} <tahun> <bulan>`\nContoh: `/{command_name} 2025 2`",
            parse_mode="Markdown"
        )
        return

    try:
        tahun = int(context.args[0])
        bulan = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ Tahun dan bulan harus berupa angka!")
        return

    data = get_data_order(tahun, bulan, order_type)

    if isinstance(data, str):
        await update.message.reply_text(f"{data}")
        return

    if not data:
        await update.message.reply_text(f"📊 Tidak ada data {order_type} untuk {tahun}-{bulan}.")
        return

    response = f"📊 *{order_type} untuk {tahun}-{bulan}:*\n\n"
    for row in data:
        response += f"📅 {row[0]}: {row[1]:,}\n"  # Menambahkan pemisah ribuan

    await update.message.reply_text(response, parse_mode="Markdown")


# Fungsi untuk menangani /jumlah_order
async def jumlah_order(update: Update, context: CallbackContext) -> None:
    await handle_order(update, context, "Jumlah Order", "jumlah_order")


# Fungsi untuk menangani /nilai_order
async def nilai_order(update: Update, context: CallbackContext) -> None:
    await handle_order(update, context, "Nilai Order", "nilai_order")

# Fungsi untuk menangani /jumlah_order_selesai
async def jumlah_order_selesai(update: Update, context: CallbackContext) -> None:
    await handle_order(update, context, "Jumlah Order Selesai", "jumlah_order_selesai")

async def nilai_order_selesai(update: Update, context: CallbackContext) -> None:
    await handle_order(update, context, "Nilai Order Selesai", "nilai_order_selesai")



async def order(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    role = get_user_role(user_id)

    if not role:
        await update.message.reply_text("⛔ Anda tidak memiliki akses. Silakan login terlebih dahulu.")
        return

    await update.message.reply_text(f"📦 Menu Order - Anda login sebagai *{role}*", parse_mode="Markdown")

async def profile(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    role = get_user_role(user_id)

    if role != "Penyedia":
        await update.message.reply_text("⛔ Menu ini hanya untuk Penyedia.")
        return

    await update.message.reply_text("👤 Profil Penyedia Anda:")

async def pembayaran(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    role = get_user_role(user_id)

    if role != "Super Admin":
        await update.message.reply_text("⛔ Menu ini hanya untuk Super Admin.")
        return

    await update.message.reply_text("💰 Menu Pembayaran:")

async def cek_data(update: Update, context: CallbackContext, jenis_data) -> None:
    try:
        # Buat koneksi ke database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query untuk mengambil data
        query = f"""
            SELECT * FROM v_cek_data_tisera 
            WHERE tanggal >= '2024-01-01'
            and hal = {jenis_data}
            ORDER BY 1 desc limit 30
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Jika tidak ada data
        if not results:
            await update.message.reply_text("Tidak ada data yang ditemukan.")
            return

        # Format hasil query
        response = "📊 *Hasil Query:*\n"
        for row in results:
            print(row)
            response += f"{row}\n"

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan: {str(e)}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def check_access(user_id):
    return user_id in USERS

async def login(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    # Cari role user di database
    role = get_user_role(user_id)

    if role:
        await update.message.reply_text(f"✅ Login berhasil! Anda masuk sebagai *{role}*.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Anda tidak memiliki akses. Hubungi admin untuk mendaftar.")


async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    role = get_user_role(user_id)

    if not role:
        await update.message.reply_text("⛔ Anda belum terdaftar. Gunakan /login untuk masuk.")
        return

    menu_text = "📌 *Menu Anda:*\n"
    menu_text += "/order - Melihat order\n"

    if role == "Penyedia":
        menu_text += "/profile - Lihat profil penyedia\n"
    elif role == "Super Admin":
        menu_text += "/pembayaran - Kelola pembayaran\n"

    await update.message.reply_text(menu_text, parse_mode="Markdown")


async def restricted_feature(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    role = get_user_role(user_id)

    if role != "Super Admin":
        await update.message.reply_text("⛔ Anda tidak memiliki akses fitur ini.")
        return

    await update.message.reply_text("✅ Fitur eksklusif ini hanya untuk Super Admin!")

async def echo(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    await update.message.reply_text(f"Kamu bilang: {text}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("order", order))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("pembayaran", pembayaran))
    app.add_handler(CommandHandler("jumlah_order", jumlah_order))
    app.add_handler(CommandHandler("nilai_order", nilai_order))
    app.add_handler(CommandHandler("jumlah_order_selesai", jumlah_order_selesai))
    app.add_handler(CommandHandler("nilai_order_selesai", nilai_order_selesai))
    app.add_handler(CommandHandler("help", help_command))

    print("Bot sedang berjalan...")
    app.run_polling()



if __name__ == "__main__":
    main()
