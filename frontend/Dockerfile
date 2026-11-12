
# Stage 1: Build React with Node.js
FROM node:22-alpine AS build

WORKDIR /app

# Install exactly the dependencies in package-lock.json
COPY package*.json ./
RUN npm ci

# Copy frontend source code
COPY . .

# The browser should call the same-origin /api path.
# Vite embeds this value at build time.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Compile TypeScript and build React
RUN npm run build

# Stage 2: Serve built files with Nginx
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
