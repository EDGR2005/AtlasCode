# Build stage
FROM node:20-alpine AS build

WORKDIR /app



COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build



# Serve stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
    
CMD ["nginx", "-g", "daemon off;"]
