FROM public.ecr.aws/lambda/nodejs:20

# Instalar FFmpeg
RUN dnf install -y ffmpeg && dnf clean all

COPY package.json ./
RUN npm install --omit=dev

COPY index.js ./

CMD ["index.handler"]
