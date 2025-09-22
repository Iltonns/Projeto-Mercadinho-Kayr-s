# Arquivo: criar_usuario.py

# Importa a função add_user do seu arquivo de lógica
from logica_banco import add_user, setup_database

# Garante que a tabela usuarios exista
setup_database()

# Cria o primeiro usuário
print("Criando o primeiro usuário...")
username = input("Digite o nome de usuário: ")
password = input("Digite a senha: ")

add_user(username, password)

print(f"Usuário '{username}' criado com sucesso!")
print("Você já pode apagar este script (criar_usuario.py) e rodar sua aplicação Flask.")