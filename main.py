"""CodynxLog: controle financeiro pessoal no terminal."""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import os
from pathlib import Path
import re
import tempfile


CAMINHO_DADOS = Path(__file__).resolve().parent / "dados.json"
DUAS_CASAS = Decimal("0.01")


def formatar_moeda(valor):
    """Retorna um valor Decimal no formato monetario brasileiro."""
    decimal = Decimal(str(valor)).quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
    texto = f"{decimal:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def converter_valor(texto):
    """Interpreta valor brasileiro e retorna Decimal arredondado para centavos.

    Um ponto seguido de exatamente tres digitos e interpretado como separador
    de milhar quando o agrupamento e valido. Assim, ``1.500`` vale 1500,00;
    ja ``1500.50`` continua sendo 1500,50. Quando houver ambiguidade, esta
    regra fixa de agrupamento de milhar tem prioridade.
    """
    if texto is None:
        raise ValueError("O valor e obrigatorio.")
    texto = str(texto).strip()
    if not texto:
        raise ValueError("Digite um valor positivo, como 150,50.")

    agrupamento_milhar = r"\d{1,3}(?:\.\d{3})+"
    formato_misto = rf"{agrupamento_milhar},\d+"
    if re.fullmatch(formato_misto, texto):
        texto_decimal = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(agrupamento_milhar, texto):
        texto_decimal = texto.replace(".", "")
    elif re.fullmatch(r"\d+(?:,\d+)?", texto):
        texto_decimal = texto.replace(",", ".")
    elif re.fullmatch(r"\d+(?:\.\d+)?", texto):
        texto_decimal = texto
    else:
        raise ValueError("Digite um valor valido, como 1.500,50.")
    try:
        valor = Decimal(texto_decimal)
    except InvalidOperation as erro:
        raise ValueError("O valor informado e invalido.") from erro
    if not valor.is_finite() or valor <= 0:
        raise ValueError("O valor deve ser maior que zero e finito.")
    return valor.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)


def validar_data(texto):
    """Valida datas ISO ou brasileiras e retorna sempre o formato ISO."""
    formatos = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
    texto = str(texto).strip() if texto is not None else ""
    for formato in formatos:
        try:
            data = datetime.strptime(texto, formato)
            return data.strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("A data deve ser valida em AAAA-MM-DD, DD-MM-AAAA ou DD/MM/AAAA.")


def validar_descricao(texto):
    descricao = str(texto).strip() if texto is not None else ""
    if not descricao:
        raise ValueError("A descricao nao pode ficar vazia.")
    return descricao


def validar_tipo(tipo):
    tipo = str(tipo).strip().lower()
    if tipo not in ("receita", "despesa"):
        raise ValueError("O tipo deve ser receita ou despesa.")
    return tipo


def validar_valor_armazenado(valor):
    """Valida valor JSON sem reinterpretar sua escrita original."""
    if not isinstance(valor, str) or not re.fullmatch(r"\d+(?:\.\d+)?", valor.strip()):
        raise ValueError("O valor armazenado deve ser um numero decimal valido.")
    try:
        decimal = Decimal(valor)
    except InvalidOperation as erro:
        raise ValueError("O valor armazenado e invalido.") from erro
    if not decimal.is_finite() or decimal <= 0:
        raise ValueError("O valor armazenado deve ser positivo e finito.")
    return decimal


def validar_movimentacao(movimentacao):
    if not isinstance(movimentacao, dict):
        raise ValueError("Cada movimentacao deve ser um dicionario.")
    campos = {"id", "tipo", "descricao", "valor", "data"}
    if set(movimentacao) != campos:
        raise ValueError("A estrutura da movimentacao e invalida.")
    identificador = movimentacao["id"]
    if isinstance(identificador, bool) or not isinstance(identificador, int) or identificador <= 0:
        raise ValueError("O ID da movimentacao e invalido.")
    validar_tipo(movimentacao["tipo"])
    validar_descricao(movimentacao["descricao"])
    validar_valor_armazenado(movimentacao["valor"])
    validar_data(movimentacao["data"])
    return {
        "id": identificador,
        "tipo": validar_tipo(movimentacao["tipo"]),
        "descricao": validar_descricao(movimentacao["descricao"]),
        "valor": movimentacao["valor"],
        "data": movimentacao["data"],
    }


def carregar_dados(caminho=CAMINHO_DADOS):
    caminho = Path(caminho)
    if not caminho.exists():
        return []
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError) as erro:
        raise ValueError(f"Nao foi possivel carregar os dados: {erro}") from erro
    if not isinstance(dados, list):
        raise ValueError("O arquivo de dados deve conter uma lista JSON.")
    try:
        registros = [validar_movimentacao(item) for item in dados]
    except ValueError as erro:
        raise ValueError(f"O arquivo de dados possui estrutura invalida: {erro}") from erro
    ids = [item["id"] for item in registros]
    if len(ids) != len(set(ids)):
        raise ValueError("O arquivo de dados possui IDs repetidos.")
    return registros


def salvar_dados(movimentacoes, caminho=CAMINHO_DADOS):
    caminho = Path(caminho)
    registros = [validar_movimentacao(item) for item in movimentacoes]
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=caminho.parent,
            prefix=f"{caminho.name}.", suffix=".tmp", delete=False
        ) as arquivo:
            temporario = Path(arquivo.name)
            json.dump(registros, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    except OSError as erro:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
        raise OSError(f"Nao foi possivel salvar os dados: {erro}") from erro


def proximo_id(movimentacoes):
    return max((item["id"] for item in movimentacoes), default=0) + 1


def calcular_saldo(movimentacoes):
    receitas = sum((Decimal(item["valor"]) for item in movimentacoes if item["tipo"] == "receita"), Decimal("0"))
    despesas = sum((Decimal(item["valor"]) for item in movimentacoes if item["tipo"] == "despesa"), Decimal("0"))
    return receitas, despesas, receitas - despesas


def ordenar_movimentacoes(movimentacoes):
    return sorted(movimentacoes, key=lambda item: (item["data"], item["id"]))


def obter_por_id(movimentacoes, identificador):
    try:
        identificador = int(str(identificador).strip())
    except (TypeError, ValueError):
        return None
    return next((item for item in movimentacoes if item["id"] == identificador), None)


def ler_entrada(mensagem, input_func=None):
    return (input if input_func is None else input_func)(mensagem).strip()


def solicitar_descricao(input_func=None, descricao_atual=None):
    while True:
        valor = ler_entrada("Descricao" + (f" [{descricao_atual}]" if descricao_atual else "") + ": ", input_func)
        if not valor and descricao_atual is not None:
            return descricao_atual
        try:
            return validar_descricao(valor)
        except ValueError as erro:
            print(erro)


def solicitar_valor(input_func=None, valor_atual=None):
    while True:
        valor = ler_entrada("Valor" + (f" [{formatar_moeda(valor_atual)}]" if valor_atual else "") + ": ", input_func)
        if not valor and valor_atual is not None:
            return f"{converter_valor(valor_atual):.2f}"
        try:
            return f"{converter_valor(valor):.2f}"
        except ValueError as erro:
            print(erro)


def solicitar_data(input_func=None, data_atual=None):
    while True:
        valor = ler_entrada("Data (AAAA-MM-DD, DD-MM-AAAA ou DD/MM/AAAA)" + (f" [{data_atual}]" if data_atual else "") + ": ", input_func)
        if not valor and data_atual is not None:
            return data_atual
        try:
            return validar_data(valor)
        except ValueError as erro:
            print(erro)


def solicitar_tipo(input_func=None, tipo_atual=None):
    while True:
        valor = ler_entrada("Tipo (receita/despesa)" + (f" [{tipo_atual}]" if tipo_atual else "") + ": ", input_func).lower()
        if not valor and tipo_atual is not None:
            return tipo_atual
        try:
            return validar_tipo(valor)
        except ValueError as erro:
            print(erro)


def adicionar_movimentacao(movimentacoes, tipo, input_func=None, output_func=None):
    saida = print if output_func is None else output_func
    tipo = validar_tipo(tipo)
    movimentacao = {
        "id": proximo_id(movimentacoes),
        "tipo": tipo,
        "descricao": solicitar_descricao(input_func),
        "valor": solicitar_valor(input_func),
        "data": solicitar_data(input_func),
    }
    movimentacoes.append(movimentacao)
    saida("Movimentacao cadastrada com sucesso.")
    return movimentacao


def consultar_saldo(movimentacoes, output_func=None):
    saida = print if output_func is None else output_func
    receitas, despesas, saldo = calcular_saldo(movimentacoes)
    saida("\n========== RESUMO FINANCEIRO ==========")
    saida(f"Total de receitas: R$ {formatar_moeda(receitas)}")
    saida(f"Total de despesas: R$ {formatar_moeda(despesas)}")
    saida(f"Saldo atual:       R$ {formatar_moeda(saldo)}")
    return receitas, despesas, saldo


def exibir_movimentacao(movimentacao, output_func=None):
    saida = print if output_func is None else output_func
    saida(f"ID: {movimentacao['id']} | Data: {movimentacao['data']} | Tipo: {movimentacao['tipo']} | "
          f"Descricao: {movimentacao['descricao']} | Valor: R$ {formatar_moeda(movimentacao['valor'])}")


def listar_movimentacoes(movimentacoes, output_func=None):
    saida = print if output_func is None else output_func
    registros = ordenar_movimentacoes(movimentacoes)
    if not registros:
        saida("Nao ha movimentacoes cadastradas.")
        return registros
    saida("\n========== MOVIMENTACOES ==========")
    for item in registros:
        exibir_movimentacao(item, saida)
    return registros


def editar_movimentacao(movimentacoes, input_func=None, output_func=None):
    saida = print if output_func is None else output_func
    item = obter_por_id(movimentacoes, ler_entrada("ID da movimentacao: ", input_func))
    if item is None:
        saida("ID inexistente.")
        return False
    saida("Pressione Enter para manter o valor atual.")
    item["descricao"] = solicitar_descricao(input_func, item["descricao"])
    item["valor"] = solicitar_valor(input_func, item["valor"])
    item["data"] = solicitar_data(input_func, item["data"])
    item["tipo"] = solicitar_tipo(input_func, item["tipo"])
    saida("Movimentacao editada com sucesso.")
    return True


def excluir_movimentacao(movimentacoes, input_func=None, output_func=None):
    saida = print if output_func is None else output_func
    item = obter_por_id(movimentacoes, ler_entrada("ID da movimentacao: ", input_func))
    if item is None:
        saida("ID inexistente.")
        return False
    exibir_movimentacao(item, saida)
    confirmacao = ler_entrada("Confirma a exclusao? (s/n): ", input_func).lower()
    if confirmacao not in ("s", "sim"):
        saida("Exclusao cancelada.")
        return False
    movimentacoes.remove(item)
    saida("Movimentacao excluida com sucesso.")
    return True


def resumo_mensal(movimentacoes, input_func=None, output_func=None):
    saida = print if output_func is None else output_func
    while True:
        mes_texto = ler_entrada("Mes (1-12): ", input_func)
        try:
            mes = int(mes_texto)
            if not 1 <= mes <= 12:
                raise ValueError
            break
        except ValueError:
            saida("O mes deve estar entre 1 e 12.")
    while True:
        ano_texto = ler_entrada("Ano: ", input_func)
        try:
            ano = int(ano_texto)
            if ano < 1:
                raise ValueError
            break
        except ValueError:
            saida("O ano informado e invalido.")
    periodo = [item for item in movimentacoes if item["data"].startswith(f"{ano:04d}-{mes:02d}-")]
    if not periodo:
        saida("Nao ha movimentacoes no periodo informado.")
        return None
    receitas, despesas, saldo = calcular_saldo(periodo)
    saida(f"\n========== RESUMO {mes:02d}/{ano:04d} ==========")
    saida(f"Receitas do periodo: R$ {formatar_moeda(receitas)}")
    saida(f"Despesas do periodo: R$ {formatar_moeda(despesas)}")
    saida(f"Saldo do periodo:    R$ {formatar_moeda(saldo)}")
    saida(f"Quantidade de movimentacoes: {len(periodo)}")
    return receitas, despesas, saldo, len(periodo)


def mostrar_menu(output_func=None):
    saida = print if output_func is None else output_func
    saida("\n================================")
    saida("           CODYNXLOG")
    saida("================================")
    saida("1 - Adicionar receita")
    saida("2 - Adicionar despesa")
    saida("3 - Consultar saldo")
    saida("4 - Listar movimentacoes")
    saida("5 - Editar movimentacao")
    saida("6 - Excluir movimentacao")
    saida("7 - Resumo mensal")
    saida("0 - Sair")


def menu(caminho=CAMINHO_DADOS, input_func=None, output_func=None):
    entrada = input if input_func is None else input_func
    saida = print if output_func is None else output_func
    try:
        movimentacoes = carregar_dados(caminho)
    except ValueError as erro:
        saida(str(erro))
        saida("O programa sera encerrado para proteger os dados originais.")
        return
    try:
        while True:
            mostrar_menu(saida)
            opcao = entrada("Escolha uma opcao: ").strip()
            if opcao == "1":
                adicionar_movimentacao(movimentacoes, "receita", entrada, saida)
                salvar_dados(movimentacoes, caminho)
            elif opcao == "2":
                adicionar_movimentacao(movimentacoes, "despesa", entrada, saida)
                salvar_dados(movimentacoes, caminho)
            elif opcao == "3":
                consultar_saldo(movimentacoes, saida)
            elif opcao == "4":
                listar_movimentacoes(movimentacoes, saida)
            elif opcao == "5":
                if editar_movimentacao(movimentacoes, entrada, saida):
                    salvar_dados(movimentacoes, caminho)
            elif opcao == "6":
                if excluir_movimentacao(movimentacoes, entrada, saida):
                    salvar_dados(movimentacoes, caminho)
            elif opcao == "7":
                resumo_mensal(movimentacoes, entrada, saida)
            elif opcao == "0":
                saida("Ate logo!")
                return
            else:
                saida("Opcao invalida.")
    except (KeyboardInterrupt, EOFError):
        saida("\nEntrada interrompida. Encerrando sem alterar os dados ja salvos.")
    except (OSError, ValueError) as erro:
        saida(f"Nao foi possivel concluir a operacao: {erro}")


if __name__ == "__main__":
    menu()
