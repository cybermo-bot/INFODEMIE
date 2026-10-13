FROM node:22-alpine
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
ENV API_INTERNAL_URL=http://api:8000
RUN npm run build
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
