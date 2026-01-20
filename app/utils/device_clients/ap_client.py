# ap_client.py

import requests
import urllib3

# Desactivar los warnings de SSL ya que los dispositivos de red a menudo
# usan certificados autofirmados, lo cual es normal en una red interna.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UbiquitiClient:
    """
    Un cliente para interactuar con la API de dispositivos Ubiquiti AirOS.
    Encapsula la lógica de autenticación y obtención de datos, reutilizando la sesión.
    """

    def __init__(self, host, username, password, port=443, http_mode=False, verify_ssl=False):
        """
        Inicializa el cliente.

        Args:
            host (str): La dirección IP del dispositivo.
            username (str): El nombre de usuario para el login.
            password (str): La contraseña para el login.
            port (int): El puerto del dispositivo.
            http_mode (bool): Si se debe usar HTTP en lugar de HTTPS.
            verify_ssl (bool): Si se debe verificar el certificado SSL. Por defecto es False.
        """
        protocol = "http" if http_mode else "https"
        self.base_url = f"{protocol}://{host}:{port}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self._is_authenticated = False

        # Añadimos un User-Agent estándar y cabeceras para mantener la conexión viva
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Connection": "keep-alive",
            }
        )

    def _authenticate(self) -> bool:
        """
        Método privado para realizar la autenticación.
        Guarda el token CSRF en la sesión si tiene éxito.

        Returns:
            bool: True si la autenticación fue exitosa, False en caso contrario.
        """
        # Limpiamos las cookies de la sesión anterior antes de autenticar
        self.session.cookies.clear()
        self._is_authenticated = False

        auth_url = self.base_url + "/api/auth"
        payload = {"username": self.username, "password": self.password}

        try:
            response = self.session.post(auth_url, data=payload, timeout=15)
            response.raise_for_status()

            csrf_token = response.headers.get("X-CSRF-ID")
            if csrf_token:
                self.session.headers.update({"X-CSRF-ID": csrf_token})
                self._is_authenticated = True
                print(f"Autenticación exitosa en {self.base_url}")
                return True

            print(f"Error de autenticación en {self.base_url}: No se recibió el token CSRF.")
            return False

        except requests.exceptions.RequestException as e:
            print(f"Error de red durante la autenticación en {self.base_url}: {e}")
            return False

    def get_status_data(self) -> dict | None:
        """
        Obtiene los datos completos de 'status.cgi' como un diccionario.
        Reutiliza la sesión si es posible, y re-autentica si la sesión ha expirado.

        Returns:
            dict | None: Un diccionario con los datos del AP si todo fue exitoso, o None si hubo algún error.
        """

        def _get_data():
            status_url = self.base_url + "/status.cgi"
            try:
                response = self.session.get(status_url, timeout=15)
                # Si la sesión expiró, el AP puede devolver 200 OK con la página de login.
                # O puede devolver 401/403.
                if response.status_code in [401, 403]:
                    print(f"Sesión para {self.base_url} expirada o no válida. Re-autenticando...")
                    return None  # Indica que se necesita re-autenticación

                response.raise_for_status()

                data = response.json()
                # A veces, incluso con 200 OK, la respuesta es la página de login (HTML).
                # Un 'status.cgi' válido siempre tiene la clave 'host'.
                if "host" not in data:
                    print(
                        f"Respuesta inesperada de {self.base_url}. Posiblemente la sesión expiró. Re-autenticando..."
                    )
                    return None  # Indica que se necesita re-autenticación

                return data

            except requests.exceptions.RequestException as e:
                print(f"Error de red al obtener datos de estado de {self.base_url}: {e}")
                raise  # Relanzamos para que el llamador sepa que hubo un error de red
            except requests.exceptions.JSONDecodeError:
                # Esto ocurre si la respuesta no es JSON, típicamente la página de login.
                print(f"La respuesta de {self.base_url} no es un JSON válido. Re-autenticando...")
                return None  # Indica que se necesita re-autenticación

        try:
            # Si no estamos autenticados, autenticamos primero.
            if not self._is_authenticated:
                if not self._authenticate():
                    print(
                        f"Fallo en la autenticación inicial para {self.base_url}, no se pueden obtener datos."
                    )
                    return None

            # Intentamos obtener los datos.
            data = _get_data()

            # Si _get_data devolvió None, la sesión expiró. Intentamos re-autenticar y re-intentar.
            if data is None:
                print("Re-intentando obtener datos después de la re-autenticación...")
                if not self._authenticate():
                    print(f"Fallo en la re-autenticación para {self.base_url}.")
                    return None

                data = _get_data()  # Re-intentamos la llamada
                if data is None:
                    print(
                        f"No se pudieron obtener datos de {self.base_url} después de re-autenticar."
                    )
                    return None

            return data

        except requests.exceptions.RequestException:
            # El error ya fue impreso en _get_data. Devolvemos None.
            return None

    def logout(self):
        """
        Cierra la sesión en el dispositivo Ubiquiti.
        """
        logout_url = self.base_url + "/api/auth/logout"
        try:
            self.session.post(logout_url, timeout=10)
            print(f"Sesión cerrada para {self.base_url}")
        except requests.exceptions.RequestException as e:
            print(f"Error al cerrar la sesión en {self.base_url}: {e}")
        finally:
            self.session.close()
            self._is_authenticated = False
