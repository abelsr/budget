FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Pinned to an exact stable tag (not a floating tag) so builds are reproducible.
# The unprivileged variant runs the master+workers as the non-root `nginx` user
# (it cannot bind :80, so it listens on 8080 — see nginx.conf and the compose port).
FROM nginxinc/nginx-unprivileged:1.29.8-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
