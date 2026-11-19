import json
from pathlib import Path
import tempfile
import unittest

import main


class CodynxLogTestes(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / "dados.json"
        self.movimentacoes = []

    def tearDown(self):
        self.pasta.cleanup()

    def entradas(self, *valores):
        iterator = iter(valores)
        return lambda _mensagem="": next(iterator)

    def test_cadastro_de_receita(self):
        item = main.adicionar_movimentacao(self.movimentacoes, "receita", self.entradas("Salario", "2000,00", "2026-11-19"), lambda _texto: None)
        self.assertEqual(item["tipo"], "receita")
        self.assertEqual(item["valor"], "2000.00")

    def test_cadastro_de_despesa(self):
        item = main.adicionar_movimentacao(self.movimentacoes, "despesa", self.entradas("Aluguel", "350.50", "2026-11-01"), lambda _texto: None)
        self.assertEqual(item["tipo"], "despesa")
        self.assertEqual(item["descricao"], "Aluguel")

    def test_calculo_de_saldo(self):
        self.movimentacoes = [
            {"id": 1, "tipo": "receita", "descricao": "A", "valor": "2000.00", "data": "2026-11-01"},
            {"id": 2, "tipo": "despesa", "descricao": "B", "valor": "350.00", "data": "2026-11-02"},
        ]
        self.assertEqual(main.calcular_saldo(self.movimentacoes), (main.Decimal("2000"), main.Decimal("350"), main.Decimal("1650")))

    def test_arredondamento_monetario(self):
        self.assertEqual(main.converter_valor("10,125"), main.Decimal("10.13"))
        self.assertEqual(main.formatar_moeda("1234.5"), "1.234,50")

    def test_formatos_monetarios_brasileiros(self):
        casos = {
            "1500": "1500.00",
            "1.500": "1500.00",
            "1.500,50": "1500.50",
            "1500,50": "1500.50",
            "1500.50": "1500.50",
            "55.00": "55.00",
            "1,50": "1.50",
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(main.converter_valor(entrada), main.Decimal(esperado))

    def test_rejeicao_de_valores_invalidos(self):
        for valor in ("0", "-1", "abc", "NaN", "Infinity", "1.000,00.2", "1..2", "1,000,00"):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    main.converter_valor(valor)

    def test_validacao_de_datas(self):
        self.assertEqual(main.validar_data("2024-02-29"), "2024-02-29")
        self.assertEqual(main.validar_data("19-11-2026"), "2026-11-19")
        self.assertEqual(main.validar_data("19/11/2026"), "2026-11-19")
        for data in ("2023-02-29", "2026-13-01", "2026-11-31", "19.11.2026"):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    main.validar_data(data)

    def test_listagem_e_ordenacao(self):
        itens = [
            {"id": 2, "tipo": "despesa", "descricao": "B", "valor": "1.00", "data": "2026-11-20"},
            {"id": 1, "tipo": "receita", "descricao": "A", "valor": "2.00", "data": "2026-11-01"},
        ]
        self.assertEqual([item["id"] for item in main.ordenar_movimentacoes(itens)], [1, 2])
        saida = []
        main.listar_movimentacoes(itens, saida.append)
        self.assertIn("ID: 1", saida[1])

    def test_edicao_de_movimentacao(self):
        item = {"id": 1, "tipo": "despesa", "descricao": "Cafe", "valor": "10.00", "data": "2026-11-01"}
        self.movimentacoes.append(item)
        resultado = main.editar_movimentacao(self.movimentacoes, self.entradas("1", "Cafe grande", "12,50", "2026-11-02", "receita"), lambda _texto: None)
        self.assertTrue(resultado)
        self.assertEqual(item, {"id": 1, "tipo": "receita", "descricao": "Cafe grande", "valor": "12.50", "data": "2026-11-02"})

    def test_edicao_mantem_campos_com_enter(self):
        item = {"id": 1, "tipo": "despesa", "descricao": "Cafe", "valor": "10.00", "data": "2026-11-01"}
        self.movimentacoes.append(item)
        main.editar_movimentacao(self.movimentacoes, self.entradas("1", "", "", "", ""), lambda _texto: None)
        self.assertEqual(item["descricao"], "Cafe")

    def test_exclusao_exige_confirmacao(self):
        item = {"id": 1, "tipo": "despesa", "descricao": "Cafe", "valor": "10.00", "data": "2026-11-01"}
        self.movimentacoes.append(item)
        self.assertFalse(main.excluir_movimentacao(self.movimentacoes, self.entradas("1", "n"), lambda _texto: None))
        self.assertEqual(len(self.movimentacoes), 1)
        self.assertTrue(main.excluir_movimentacao(self.movimentacoes, self.entradas("1", "s"), lambda _texto: None))
        self.assertEqual(self.movimentacoes, [])

    def test_persistencia_em_json(self):
        dados = [{"id": 1, "tipo": "receita", "descricao": "Acentuacao", "valor": "10.00", "data": "2026-11-19"}]
        main.salvar_dados(dados, self.caminho)
        self.assertEqual(main.carregar_dados(self.caminho), dados)
        conteudo = self.caminho.read_text(encoding="utf-8")
        self.assertIn("Acentuacao", conteudo)

    def test_carregamento_de_dados_existentes(self):
        self.caminho.write_text(json.dumps([{"id": 4, "tipo": "despesa", "descricao": "Conta", "valor": "3456.78", "data": "2026-11-01"}], ensure_ascii=False), encoding="utf-8")
        dados = main.carregar_dados(self.caminho)
        self.assertEqual(dados[0]["valor"], "3456.78")

    def test_valor_existente_ambiguo_nao_e_reinterpretado(self):
        original = [{"id": 4, "tipo": "receita", "descricao": "Registro antigo", "valor": "1.500", "data": "2026-11-01"}]
        self.caminho.write_text(json.dumps(original), encoding="utf-8")
        dados = main.carregar_dados(self.caminho)
        self.assertEqual(dados[0]["valor"], "1.500")
        main.salvar_dados(dados, self.caminho)
        novamente = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertEqual(novamente[0]["valor"], "1.500")

    def test_arquivo_json_corrompido(self):
        self.caminho.write_text("{ arquivo invalido", encoding="utf-8")
        with self.assertRaises(ValueError):
            main.carregar_dados(self.caminho)

    def test_ids_unicos_apos_exclusao(self):
        self.movimentacoes.extend([
            {"id": 1, "tipo": "receita", "descricao": "A", "valor": "1.00", "data": "2026-11-01"},
            {"id": 2, "tipo": "receita", "descricao": "B", "valor": "1.00", "data": "2026-11-02"},
        ])
        self.movimentacoes.pop(0)
        novo = main.adicionar_movimentacao(self.movimentacoes, "receita", self.entradas("C", "1", "2026-11-03"), lambda _texto: None)
        self.assertEqual(novo["id"], 3)

    def test_resumo_mensal(self):
        self.movimentacoes = [
            {"id": 1, "tipo": "receita", "descricao": "A", "valor": "2000.00", "data": "2026-11-01"},
            {"id": 2, "tipo": "despesa", "descricao": "B", "valor": "350.00", "data": "2026-11-02"},
            {"id": 3, "tipo": "despesa", "descricao": "C", "valor": "5.00", "data": "2026-10-01"},
        ]
        resumo = main.resumo_mensal(self.movimentacoes, self.entradas("13", "11", "2026"), lambda _texto: None)
        self.assertEqual(resumo, (main.Decimal("2000"), main.Decimal("350"), main.Decimal("1650"), 2))

    def test_menu_e_saida(self):
        saida = []
        main.menu(self.caminho, self.entradas("9", "0"), saida.append)
        self.assertIn("Opcao invalida.", saida)
        self.assertIn("Ate logo!", saida)

    def test_menu_encerramento_por_eof(self):
        def gerar_eof(_mensagem=""):
            raise EOFError

        saida = []
        main.menu(self.caminho, gerar_eof, saida.append)
        self.assertTrue(any("Entrada interrompida" in texto for texto in saida))

    def test_menu_encerramento_por_ctrl_c(self):
        def gerar_ctrl_c(_mensagem=""):
            raise KeyboardInterrupt

        saida = []
        main.menu(self.caminho, gerar_ctrl_c, saida.append)
        self.assertTrue(any("Entrada interrompida" in texto for texto in saida))

    def test_menu_cadastra_e_persiste(self):
        main.menu(self.caminho, self.entradas("1", "Salario", "2000,00", "2026-11-19", "0"), lambda _texto: None)
        self.assertEqual(len(main.carregar_dados(self.caminho)), 1)


if __name__ == "__main__":
    unittest.main()
