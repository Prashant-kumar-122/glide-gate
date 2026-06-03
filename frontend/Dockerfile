FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source
COPY . .

# Build check - verify frontend compiles without errors
RUN npm run build

# Expose Vite dev server port
EXPOSE 5173

# Run dev server
CMD ["npm", "run", "dev"]
