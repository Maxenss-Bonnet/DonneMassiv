
# Étape 1 : construire l'app React
FROM node:20 AS build

WORKDIR /app
COPY . .
RUN npm install
RUN npm run build

# Étape 2 : servir l'app avec un serveur web léger (nginx)
FROM nginx:alpine

# Copier les fichiers de build dans nginx
COPY --from=build /app/build /usr/share/nginx/html
