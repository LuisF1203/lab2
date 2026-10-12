#!/usr/bin/env python3
"""
Menú simple de consola en Python para realizar peticiones REST.
CRUD de películas sobre la API con MongoDB: insertar (una o varias),
consultar por nombre / director / género, actualizar y borrar.
"""
import os
import sys
import requests

API_URL = os.getenv('API_URL', 'http://localhost:8001')
MOVIES_URL = f"{API_URL}/movies"


# ---------------------------------------------------------------------------
# Utilidades de entrada / salida
# ---------------------------------------------------------------------------

def mostrar_respuesta(response):
    """Imprime el código de estado y el mensaje de error, si lo hay."""
    print(f"Código de estado: {response.status_code}")
    if response.status_code >= 400:
        print("Respuesta:", response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text)


def mostrar_peliculas(movies):
    """Imprime una lista de películas en forma de tabla."""
    if not movies:
        print("No se encontraron películas.")
        return
    print(f"{'ID':<24}  {'Título':<26} {'Año':<5} {'Director':<22} {'Género':<34} {'Rating'}")
    print("-" * 122)
    for m in movies:
        generos = ", ".join(m.get('genre', []))
        print(f"{m['_id']:<24}  {m.get('title', '')[:26]:<26} {str(m.get('year', '')):<5} "
              f"{m.get('director', '')[:22]:<22} {generos[:34]:<34} {m.get('rating', '')}")
    print(f"Total: {len(movies)}")


def pedir_pelicula():
    """Solicita los datos de una película y regresa el documento a enviar."""
    titulo = input("Título: ").strip()
    anio = input("Año: ").strip()
    director = input("Director: ").strip()
    generos = input("Género(s) separados por coma: ").strip()
    rating = input("Rating: ").strip()

    movie = {"title": titulo, "director": director}
    if anio:
        movie["year"] = int(anio)
    if generos:
        movie["genre"] = [g.strip() for g in generos.split(",") if g.strip()]
    if rating:
        movie["rating"] = float(rating)
    # Enviar solo campos con valor
    return {k: v for k, v in movie.items() if v}


def elegir_pelicula(accion):
    """
    Busca por título la película sobre la que se hará la acción y regresa
    el documento elegido (pide escoger si hay varias coincidencias).
    """
    titulo = input(f"Título de la película a {accion}: ").strip()
    if not titulo:
        print("[AVISO] El título no puede estar vacío.")
        return None
    response = requests.get(MOVIES_URL, params={"title": titulo}, timeout=10)
    movies = response.json().get('data', [])
    mostrar_peliculas(movies)
    if not movies:
        return None
    if len(movies) == 1:
        return movies[0]
    opcion = input(f"Selecciona el número de película [1-{len(movies)}]: ").strip()
    if not opcion.isdigit() or not 1 <= int(opcion) <= len(movies):
        print("[AVISO] Selección no válida.")
        return None
    return movies[int(opcion) - 1]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def insertar_pelicula():
    """POST /movies con una sola película."""
    print(f"\n[INFO] Insertar película en: {MOVIES_URL}")
    try:
        response = requests.post(MOVIES_URL, json=pedir_pelicula(), timeout=10)
        mostrar_respuesta(response)
        if response.status_code == 201:
            mostrar_peliculas([response.json()['item']])
    except ValueError:
        print("[ERROR] Año y rating deben ser números.")
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] Error en petición REST: {err}")


def insertar_varias():
    """POST /movies con un arreglo de películas (insert_many)."""
    print(f"\n[INFO] Insertar varias películas en: {MOVIES_URL}")
    try:
        cantidad = int(input("¿Cuántas películas vas a insertar?: ").strip())
        movies = []
        for i in range(1, cantidad + 1):
            print(f"\n-- Película {i} de {cantidad} --")
            movies.append(pedir_pelicula())
        response = requests.post(MOVIES_URL, json=movies, timeout=10)
        print()
        mostrar_respuesta(response)
        if response.status_code == 201:
            mostrar_peliculas(response.json()['data'])
    except ValueError:
        print("[ERROR] Cantidad, año y rating deben ser números.")
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] Error en petición REST: {err}")


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def consultar_todas():
    """GET /movies"""
    print(f"\n[INFO] Consultando películas en: {MOVIES_URL}")
    try:
        response = requests.get(MOVIES_URL, timeout=10)
        mostrar_respuesta(response)
        mostrar_peliculas(response.json().get('data', []))
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] Error en petición REST: {err}")


def consultar_por(campo, etiqueta):
    """GET /movies?<campo>=<valor>"""
    valor = input(f"{etiqueta} a buscar: ").strip()
    if not valor:
        print(f"[AVISO] El {etiqueta.lower()} no puede estar vacío.")
        return
    print(f"\n[INFO] Consultando en: {MOVIES_URL}?{campo}={valor}")
    try:
        response = requests.get(MOVIES_URL, params={campo: valor}, timeout=10)
        mostrar_respuesta(response)
        mostrar_peliculas(response.json().get('data', []))
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] Error en petición REST: {err}")


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def actualizar_pelicula():
    """PUT /movies/{id} — Enter deja el valor actual sin cambios."""
    try:
        movie = elegir_pelicula("actualizar")
        if not movie:
            return
        print("\nEscribe el nuevo valor o deja vacío para conservar el actual.")
        cambios = {}
        for campo, etiqueta in (("title", "Título"), ("year", "Año"), ("director", "Director"),
                                ("genre", "Género(s)"), ("rating", "Rating")):
            actual = movie.get(campo, '')
            mostrado = ", ".join(actual) if isinstance(actual, list) else actual
            nuevo = input(f"{etiqueta} [{mostrado}]: ").strip()
            if not nuevo:
                continue
            if campo == "year":
                nuevo = int(nuevo)
            elif campo == "rating":
                nuevo = float(nuevo)
            elif campo == "genre":
                nuevo = [g.strip() for g in nuevo.split(",") if g.strip()]
            cambios[campo] = nuevo
        if not cambios:
            print("[AVISO] No se modificó ningún campo.")
            return
        url = f"{MOVIES_URL}/{movie['_id']}"
        print(f"\n[INFO] Actualizando película en: {url}")
        response = requests.put(url, json=cambios, timeout=10)
        mostrar_respuesta(response)
        if response.ok:
            mostrar_peliculas([response.json()['item']])
    except ValueError:
        print("[ERROR] Año y rating deben ser números.")
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] Error en petición REST: {err}")


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def eliminar_pelicula():
    """DELETE /movies/{id}"""
    try:
        movie = elegir_pelicula("eliminar")
        if not movie:
            return
        confirmar = input(f"¿Eliminar '{movie['title']}'? [s/N]: ").strip().lower()
        if confirmar != 's':
            print("Operación cancelada.")
            return
        url = f"{MOVIES_URL}/{movie['_id']}"
        print(f"\n[INFO] Eliminando película en: {url}")
        response = requests.delete(url, timeout=10)
        mostrar_respuesta(response)
        if response.ok:
            print(response.json()['message'])
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] Error en petición REST: {err}")


def mostrar_menu():
    """Despliega el menú de opciones en pantalla."""
    print("\n" + "=" * 55)
    print("        MENÚ PRINCIPAL - PELÍCULAS (MongoDB)")
    print("=" * 55)
    print(f" Servidor objetivo: {API_URL}")
    print("-" * 55)
    print(" 1. Insertar una película        (POST /movies)")
    print(" 2. Insertar varias películas    (POST /movies)")
    print(" 3. Consultar todas              (GET /movies)")
    print(" 4. Consultar por nombre         (GET /movies?title=)")
    print(" 5. Consultar por director       (GET /movies?director=)")
    print(" 6. Consultar por género         (GET /movies?genre=)")
    print(" 7. Actualizar una película      (PUT /movies/{id})")
    print(" 8. Eliminar una película        (DELETE /movies/{id})")
    print(" 0. Salir")
    print("=" * 55)


def main():
    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción [0-8]: ").strip()

        if opcion == '1':
            insertar_pelicula()
        elif opcion == '2':
            insertar_varias()
        elif opcion == '3':
            consultar_todas()
        elif opcion == '4':
            consultar_por("title", "Nombre")
        elif opcion == '5':
            consultar_por("director", "Director")
        elif opcion == '6':
            consultar_por("genre", "Género")
        elif opcion == '7':
            actualizar_pelicula()
        elif opcion == '8':
            eliminar_pelicula()
        elif opcion == '0':
            print("\nSaliendo del programa. ¡Hasta luego!")
            sys.exit(0)
        else:
            print("\n[AVISO] Opción no válida. Por favor, ingresa un número del 0 al 8.")


if __name__ == '__main__':
    main()
