FROM nginx:alpine

# Kopiowanie konfiguracji reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Kopiowanie plików statycznych PWA do domyślnego katalogu Nginxa
COPY . /usr/share/nginx/html

EXPOSE 80