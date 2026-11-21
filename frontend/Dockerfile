# --- base: dependências ---
FROM node:20-alpine AS base
WORKDIR /app
COPY package.json ./
RUN npm install

# --- dev: Vite com hot reload ---
FROM base AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# --- build: gera estáticos ---
FROM base AS build
COPY . .
RUN npm run build

# --- prod: nginx servindo o build ---
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
