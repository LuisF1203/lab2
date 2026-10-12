#!/usr/bin/env python3
"""
Capa de modelo de base de datos para MongoDB.

CRUD de películas: cada película es un documento de la colección 'movies'
con los campos title, year, director, genre (arreglo) y rating.
"""
import logging
import re
import time
from bson.objectid import ObjectId
from pymongo import MongoClient, ReturnDocument

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conexión a MongoDB
# ---------------------------------------------------------------------------

class MongoConnection:

    def __init__(self, host='localhost', port=27017, database='movies_db'):
        self.host = host
        self.port = port
        self.database_name = database
        self.client = None
        self.db = None

    def connect(self, retries=5, delay=5):
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                log.info(f"Conectando a MongoDB en {self.host}:{self.port} (intento {attempt}/{retries})")
                self.client = MongoClient(
                    host=self.host,
                    port=self.port,
                    serverSelectionTimeoutMS=5000,
                )
                # Verificar conectividad inmediata con ping
                self.client.admin.command('ping')
                self.db = self.client[self.database_name]
                return True
            except Exception as e:
                last_exc = e
                log.warning(f"Fallo de conexión ({attempt}/{retries}): {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise last_exc

    def close(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

    def is_connected(self):
        if self.client is None:
            return False
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Definición de Colecciones e Índices
# ---------------------------------------------------------------------------

DEFAULT_COLLECTION = 'movies'

# Campos por los que la aplicación permite buscar películas
SEARCH_FIELDS = ('title', 'director', 'genre')

# Lista de índices: (colección, campos, opciones)
ALL_INDEXES = [
    (DEFAULT_COLLECTION, [('title', 1)], {'name': 'idx_title'}),
    (DEFAULT_COLLECTION, [('director', 1)], {'name': 'idx_director'}),
    (DEFAULT_COLLECTION, [('genre', 1)], {'name': 'idx_genre'}),
]


def create_indexes(db):
    """
    Crea los índices configurados en ALL_INDEXES.
    En MongoDB, los índices definen el rendimiento de las consultas y
    representan el equivalente al DDL en bases de datos relacionales/Cassandra.
    """
    created = []
    for coll_name, keys, options in ALL_INDEXES:
        log.info(f"Creando índice en colección '{coll_name}': {keys}")
        coll = db[coll_name]
        idx_name = coll.create_index(keys, **options)
        created.append({'collection': coll_name, 'index': idx_name})
    return created


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _serialize(doc):
    """Convierte el '_id' (ObjectId) a string para poder enviarlo como JSON."""
    if doc:
        doc['_id'] = str(doc['_id'])
    return doc


def _id_query(movie_id: str):
    """Construye el filtro por '_id' aceptando ObjectId o un identificador exacto."""
    if ObjectId.is_valid(movie_id):
        return {'_id': ObjectId(movie_id)}
    return {'_id': movie_id}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def insert_movie(db, movie: dict):
    """Inserta una sola película (insert_one) y la regresa con su '_id'."""
    doc = dict(movie)
    result = db[DEFAULT_COLLECTION].insert_one(doc)
    doc['_id'] = str(result.inserted_id)
    return doc


def insert_movies(db, movies: list):
    """Inserta varias películas en una sola operación (insert_many)."""
    docs = [dict(m) for m in movies]
    result = db[DEFAULT_COLLECTION].insert_many(docs)
    for doc, new_id in zip(docs, result.inserted_ids):
        doc['_id'] = str(new_id)
    return docs


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_movies(db, limit=100):
    """Consulta todas las películas de la colección."""
    cursor = db[DEFAULT_COLLECTION].find().sort('title', 1).limit(limit)
    return [_serialize(doc) for doc in cursor]


def get_movies_by(db, field: str, value: str, limit=100):
    """
    Consulta películas por nombre (title), director o género (genre).
    La búsqueda no distingue mayúsculas y acepta coincidencias parciales;
    en 'genre' (arreglo) basta con que alguno de los géneros coincida.
    """
    if field not in SEARCH_FIELDS:
        raise ValueError(f"Campo de búsqueda no válido: {field}")
    query = {field: {'$regex': re.escape(value), '$options': 'i'}}
    cursor = db[DEFAULT_COLLECTION].find(query).sort('title', 1).limit(limit)
    return [_serialize(doc) for doc in cursor]


def get_movie_by_id(db, movie_id: str):
    """Consulta una película por su '_id'."""
    return _serialize(db[DEFAULT_COLLECTION].find_one(_id_query(movie_id)))


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update_movie(db, movie_id: str, changes: dict):
    """
    Actualiza solo los campos recibidos ($set) y regresa la película ya
    modificada, o None si no existe.
    """
    changes = {k: v for k, v in changes.items() if k != '_id'}
    doc = db[DEFAULT_COLLECTION].find_one_and_update(
        _id_query(movie_id),
        {'$set': changes},
        return_document=ReturnDocument.AFTER,
    )
    return _serialize(doc)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_movie(db, movie_id: str):
    """Elimina una película por su '_id'. Regresa True si se borró."""
    result = db[DEFAULT_COLLECTION].delete_one(_id_query(movie_id))
    return result.deleted_count > 0
