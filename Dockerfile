# Kichik va yengil Python versiyasini tanlaymiz
FROM python:3.10-slim

# Konteyner ichida ishchi papka yaratamiz
WORKDIR /app

# Talab qilinadigan kutubxonalar ro'yxatini nusxalaymiz
COPY requirements.txt .

# Kutubxonalarni o'rnatamiz
RUN pip install --no-cache-dir -r requirements.txt

# Barcha kodlarni konteynerga o'tkazamiz
COPY . .

# Botni ishga tushirish buyrug'i
CMD ["python", "main.py"]