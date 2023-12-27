# URL Shortener

Este proyecto es un acortador de URLs simple. Utiliza [Redis](https://redis.io/) para el almacenamiento en memoria de las URLs acortadas,
lo que permite una recuperación rápida y eficiente. Si una URL no se encuentra en Redis, esta es buscada en [Turso](https://turso.tech/).

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración de Redis](#configuración-de-redis)
- [Configuración de Turso](#configuración-de-turso)
- [Uso](#uso)
- [Manejo de errores](#manejo-de-errores)
- [Tests](#tests)

## Requisitos

- [Python 3.12.1](https://www.python.org/)
- [Redis](https://redis.io/)
- [Turso](https://turso.tech/)
- [pytest 7.4.3](https://pytest.org/)

## Instalación

1. Clonar el repositorio

```sh
git clone https://github.com/Catrilao/url-shortener.git
```

2. Instalar las dependencias

```sh
pip install -r requirements.txt
```

3. Crear archivo .env en la raíz del proyecto y llenar con las variables de entorno

[Como obtener las variables de entorno de Redis](#configuración-de-redis)

[Como obtener las variables de entorno de Turso](#configuración-de-turso)

```txt
REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=

TURSO_DB_URL=
TURSO_DB_AUTH_TOKEN=
```

4. Ejecutar la aplicación

```sh
python main.py
```

## Configuración de Redis

1. Ve a [Redis Labs](https://app.redislabs.com/#/subscriptions/) y crea una nueva suscripción.
2. Una vez que hayas creado la suscripción, crea una nueva base de datos.
3. Después de crear la base de datos, haz clic en el botón "conectar".
4. En la página de conexión, selecciona "Redis Client" y luego "Python".
5. Copia los valores de host, port y password que se muestran.
6. Crea un archivo `.env` en la raíz de tu proyecto y pega los valores de host, port y password

```txt
REDIS_HOST=
REDIS_PORT=
REDIS_PASSWORD=
```

## Configuración de Turso

1. Instala la CLI de Turso siguiendo las instrucciones disponibles [aquí](https://docs.turso.tech/reference/turso-cli#installation).

2. Una vez instalada la CLI de Turso, crea una nueva base de datos con el siguiente comando:

```sh
turso db create [NOMBRE-BD]
```

3. Ingresa a la base de datos:

```sh
turso db shell [NOMBRE-BD]
```

4. Crea la tabla donde se almacenarán las URLs

```sql
CREATE TABLE urls (
  short_url TEXT PRIMARY KEY,
  original_url TEXT
);
``` 

### Agregar Turso al proyecto

Para acceder a la base de datos, necesitas la url de tu base de datos Turso y un token de autenticación.

1. Para obtener la url de la base de datos, ejecuta este comando:

```sh
turso db show [NOMBRE-BD] --url
```

2. Para crear un token de autenticación:
```sh
turso db tokens create [NOMBRE-BD] --expiration none
```

4. Crea un archivo `.env` en la raíz del proyecto copia la url de la base de datos y el token de autenticación:

```txt
TURSO_DB_URL=
TURSO_DB_AUTH_TOKEN=
```


## Uso

La aplicación tiene dos rutas:

- `GET /` : Página principal donde se pueden acortar las URLs.
- `GET /<short-url>` : Redirecciona a la url original asociado a la URL acortada.

## Manejo de errores

La aplicación hara logs de los errores a la consola. Maneja errores relacionados a las conecciones de Redis y Turso, almacenamiento y devolución de URLs.

## Tests

Este proyecto usa pytest para el testeo. Para correr todos los tests, puedes usar este comando:

```sh
pytest
```

Para ejecutar los tests de manera singular:
  
- Este test prueba las conneciones a Redis y Turso
```sh
pytest tests/test_get_connections.py
```

- Este test prueba la función que guarda las URLs
```sh
pytest tests/test_store_url.py
```

- Este test prueba la función que devuelve las URLs
```sh
pytest tests/test_get_url.py
  ```
