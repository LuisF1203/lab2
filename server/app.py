#!/usr/bin/env python3
"""
Aplicación Falcon ASGI para la API REST con MongoDB.
"""
import logging
import os
import falcon.asgi

from model import MongoConnection
from resources import (
    SetupResource,
    MoviesResource,
    MovieResource,
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger(__name__)

# Lectura de variables de entorno
MONGODB_HOST = os.getenv('MONGODB_HOST', 'localhost')
MONGODB_PORT = int(os.getenv('MONGODB_PORT', '27017'))
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'movies_db')


class LoggingMiddleware:
    """Middleware para registro de peticiones y respuestas."""

    async def process_request(self, req, resp):
        log.info(f"Petición: {req.method} {req.uri}")

    async def process_response(self, req, resp, resource, req_succeeded):
        log.info(f"Respuesta: {resp.status} para {req.method} {req.uri}")


class CORSMiddleware:
    """Middleware para encabezados CORS."""

    async def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        resp.set_header('Access-Control-Allow-Headers', 'Content-Type')


def create_app():
    """Crea y configura la aplicación Falcon ASGI."""
    connection = MongoConnection(
        host=MONGODB_HOST,
        port=MONGODB_PORT,
        database=MONGODB_DATABASE,
    )

    try:
        connection.connect()
        log.info(f"Conexión exitosa a MongoDB en {MONGODB_HOST}:{MONGODB_PORT}")
    except Exception as e:
        log.error(f"Fallo al conectar con MongoDB: {e}")
        raise

    app = falcon.asgi.App(middleware=[
        LoggingMiddleware(),
        CORSMiddleware(),
    ])

    # Instanciación de recursos
    setup_resource = SetupResource(connection)
    movies_resource = MoviesResource(connection)
    movie_resource = MovieResource(connection)

    # Registro de rutas REST
    app.add_route('/setup', setup_resource)
    app.add_route('/movies', movies_resource)
    app.add_route('/movies/{movie_id}', movie_resource)

    log.info("Rutas registradas:")
    log.info("  POST   /setup")
    log.info("  GET    /movies   (?title= | ?director= | ?genre=)")
    log.info("  POST   /movies   (una película o un arreglo)")
    log.info("  GET    /movies/{movie_id}")
    log.info("  PUT    /movies/{movie_id}")
    log.info("  DELETE /movies/{movie_id}")

    return app


app = create_app()
