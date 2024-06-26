# tailwindcss cli

cd tailwindcss
./tailwindcss-windows-x64-v3.4.3.exe -i ../app/static/tailwind-input.css -o ../app/static/tailwind-output.css

# Start a watcher

./tailwindcss-windows-x64-v3.4.3.exe -i ../app/static/tailwind-input.css -o ../app/static/tailwind-output.css --watch

# Compile and minify your CSS for production

./tailwindcss-windows-x64-v3.4.3.exe -i ../app/static/tailwind-input.css -o ../app/static/tailwind-output.css --minify

. venv/Scripts/activate
cd app
fastapi dev main.py

