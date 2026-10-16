FROM node:22-alpine
WORKDIR /service
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY tsconfig.json next-env.d.ts ./
COPY app/ ./app/
COPY lib/ ./lib/
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
