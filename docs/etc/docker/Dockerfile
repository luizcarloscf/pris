FROM zensical/zensical:0.1.0 AS build

WORKDIR /docs
COPY zensical.toml ./
COPY content ./content
RUN zensical build --strict --clean

FROM nginx:1.30.6-alpine

COPY etc/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /docs/site /usr/share/nginx/html
