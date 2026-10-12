#!/usr/bin/env python3
"""
Clases de recursos Falcon para la API REST con MongoDB.
Expone el CRUD de películas: inserción (una o varias), consultas por
nombre/director/género, actualización y borrado.
"""
import logging
import falcon
import model

log = logging.getLogger(__name__)

# Campos que se aceptan al insertar o actualizar una película
MOVIE_FIELDS = ('title', 'year', 'director', 'genre', 'rating')


def clean_movie(data: dict):
    """Deja solo los campos válidos de una película."""
    return {k: v for k, v in data.items() if k in MOVIE_FIELDS}


class SetupResource:
    """Endpoint administrativo para crear colecciones e índices en MongoDB."""

    def __init__(self, conn):
        self.conn = conn

    async def on_post(self, req, resp):
        """POST /setup"""
        try:
            indexes = model.create_indexes(self.conn.db)
            resp.media = {
                'status': 'success',
                'message': f'Base de datos {self.conn.database_name} e índices creados exitosamente',
                'indexes': indexes,
                'note': 'MongoDB no requiere esquema rígido; los índices definen el rendimiento de consultas.',
            }
            resp.status = falcon.HTTP_201
        except Exception as e:
            log.exception("Fallo al ejecutar setup")
            resp.media = {'status': 'error', 'message': str(e)}
            resp.status = falcon.HTTP_500


class MoviesResource:
    """
    Recurso de la colección de películas.
    GET  /movies  — todas, o filtradas por ?title= / ?director= / ?genre=
    POST /movies  — inserta una película (objeto JSON) o varias (arreglo JSON)
    """

    def __init__(self, conn):
        self.conn = conn

    async def on_get(self, req, resp):
        """GET /movies"""
        try:
            limit = req.get_param_as_int('limit') or 100
            filtro = next(
                ((campo, req.get_param(campo)) for campo in model.SEARCH_FIELDS if req.get_param(campo)),
                None,
            )
            if filtro:
                movies = model.get_movies_by(self.conn.db, *filtro, limit=limit)
            else:
                movies = model.get_movies(self.conn.db, limit=limit)
            resp.media = {'count': len(movies), 'data': movies}
        except Exception as e:
            log.exception("Error al consultar películas")
            resp.media = {'error': str(e)}
            resp.status = falcon.HTTP_500

    async def on_post(self, req, resp):
        """POST /movies"""
        try:
            body = await req.get_media()
            if not body:
                resp.media = {'error': "Cuerpo JSON requerido"}
                resp.status = falcon.HTTP_400
                return

            if isinstance(body, list):
                movies = [clean_movie(m) for m in body]
                if not all(m.get('title') for m in movies):
                    resp.media = {'error': "Todas las películas requieren 'title'"}
                    resp.status = falcon.HTTP_400
                    return
                inserted = model.insert_movies(self.conn.db, movies)
                resp.media = {'status': 'created', 'count': len(inserted), 'data': inserted}
            else:
                movie = clean_movie(body)
                if not movie.get('title'):
                    resp.media = {'error': "El campo 'title' es obligatorio"}
                    resp.status = falcon.HTTP_400
                    return
                inserted = model.insert_movie(self.conn.db, movie)
                resp.media = {'status': 'created', 'item': inserted}
            resp.status = falcon.HTTP_201
        except Exception as e:
            log.exception("Error al insertar película(s)")
            resp.media = {'error': str(e)}
            resp.status = falcon.HTTP_500


class MovieResource:
    """
    Recurso de una película específica por su '_id'.
    GET / PUT / DELETE /movies/{movie_id}
    """

    def __init__(self, conn):
        self.conn = conn

    def _not_found(self, resp, movie_id):
        resp.media = {'error': f'Película con ID {movie_id} no encontrada'}
        resp.status = falcon.HTTP_404

    async def on_get(self, req, resp, movie_id):
        """GET /movies/{movie_id}"""
        try:
            movie = model.get_movie_by_id(self.conn.db, movie_id)
            if not movie:
                return self._not_found(resp, movie_id)
            resp.media = {'status': 'success', 'item': movie}
        except Exception as e:
            log.exception(f"Error al consultar película {movie_id}")
            resp.media = {'error': str(e)}
            resp.status = falcon.HTTP_500

    async def on_put(self, req, resp, movie_id):
        """PUT /movies/{movie_id} — actualiza solo los campos enviados"""
        try:
            changes = clean_movie(await req.get_media() or {})
            if not changes:
                resp.media = {'error': "No se recibieron campos para actualizar"}
                resp.status = falcon.HTTP_400
                return
            movie = model.update_movie(self.conn.db, movie_id, changes)
            if not movie:
                return self._not_found(resp, movie_id)
            resp.media = {'status': 'updated', 'item': movie}
        except Exception as e:
            log.exception(f"Error al actualizar película {movie_id}")
            resp.media = {'error': str(e)}
            resp.status = falcon.HTTP_500

    async def on_delete(self, req, resp, movie_id):
        """DELETE /movies/{movie_id}"""
        try:
            if not model.delete_movie(self.conn.db, movie_id):
                return self._not_found(resp, movie_id)
            resp.media = {'status': 'success', 'message': f'Película {movie_id} eliminada exitosamente'}
        except Exception as e:
            log.exception(f"Error al eliminar película {movie_id}")
            resp.media = {'error': str(e)}
            resp.status = falcon.HTTP_500
