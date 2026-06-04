import os
import sys
import sqlite3
from datetime import datetime, date

# Quando executado como .exe PyInstaller, usar o directório do executável
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(_BASE_DIR, 'gestao_documentos.db')


class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS documentos_recebidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            proveniencia TEXT,
            remetente_nome TEXT,
            remetente_cargo TEXT,
            assunto TEXT NOT NULL,
            data_recepcao TEXT,
            despacho TEXT,
            endereçado_a TEXT,
            tecnico TEXT,
            data_resposta TEXT,
            prazo_status TEXT DEFAULT 'Pendente',
            observacao TEXT,
            ficheiro_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS documentos_enviados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT,
            assunto TEXT NOT NULL,
            preparado_por TEXT,
            assinante TEXT,
            destinatario_nome TEXT,
            destinatario_cargo TEXT,
            instituicao TEXT,
            data_envio TEXT,
            ficheiro_path TEXT,
            observacao TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS reunioes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_doc TEXT,
            organizador TEXT,
            data_convocatoria TEXT,
            assunto TEXT NOT NULL,
            data_reuniao TEXT,
            hora_local TEXT,
            link_convocatoria TEXT,
            participantes TEXT,
            contactos TEXT,
            decisoes TEXT,
            ficheiro_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            departamento TEXT,
            cargo TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )''')

        conn.commit()

        # Load initial data only if tables are empty
        c.execute("SELECT COUNT(*) FROM documentos_recebidos")
        if c.fetchone()[0] == 0:
            self._load_initial_recebidos(c)

        c.execute("SELECT COUNT(*) FROM contactos")
        if c.fetchone()[0] == 0:
            self._load_initial_contactos(c)

        conn.commit()
        conn.close()

    def _load_initial_recebidos(self, c):
        records = [
            ('Oficio n° 220/MPD/GM/DNEIC/2025', 'MPD-GM', 'Salimo Cripton Vala', 'Ministro',
             'Harmonização da Lista de Projectos', '2025-01-16', 'Dir. Ortigio Nhanombe',
             'Dep. Planeamento Energético', 'Iazalde Jose Jeremias', '2025-01-21', 'Dentro do Prazo', None),
            ('Ref. 334/MIREME/DPC/DC/010,4/25', 'MIREME-DPC', 'Maria Joel', 'Directora',
             'Solicitação de Ponto de Situação da Cooperação com a India', '2024-12-20', 'Dir. Ortigio Nhanombe',
             'Dep. Planeamento Energético', 'Iazalde Jose Jeremias', '2024-12-28', 'Fora do Prazo',
             'Fora do Prazo resultante da Tolerância de Ponto decretada no dia 2 de Janeiro'),
            ('Ref. 003/MIREME/DPC/DC/004/26', 'MIREME-DPC', 'Ine Chalufo', 'Directora Adj.',
             'Pedido de Parecer sobre a Proposta do Memorando Moç-EAU', '2025-01-30', 'Dir. Ortigio Nhanombe',
             'Dep. Planeamento Energético', 'Iazalde Jose Jeremias', '2025-01-31', 'Dentro do Prazo', None),
            ('Ref. 478/MIREME/DPC/DC/920/25', 'MIREME-DPC', 'Maria Joel', 'Directora',
             'Comunicado de Despacho Coreia do Sul', '2026-02-19', 'Dir. Ortigio Nhanombe',
             'Dep. Planeamento Energético', 'Iazalde Jose Jeremias', '2026-02-21', 'Dentro do Prazo', None),
            ('Nota n° 15/MIREME/DPC-DC/004/2026', 'MIREME-DPC', 'Ine Chalufo', 'Directora Adj.',
             'Preparação da Proposta do Plano e Orçamento Pós-Cheias 2026', '2026-02-22', 'Dir. Ortigio Nhanombe',
             'Dep. Planeamento Energético', 'Iazalde Jose Jeremias', '2026-02-22', 'Dentro do Prazo', None),
            ('Our Ref. n° 01/GM/MF/DNTCF/2026', 'MF-GM', 'Carla Loveira', 'Ministra',
             'Status of Mozambiques Application to ATIDI', '2026-02-22', 'Dir. Ortigio Nhanombe',
             'Dep. Planeamento Energético', 'Iazalde Jose Jeremias', '2026-02-22', 'Arquivado', None),
            ('Oficio n° 10/GEPR/2026', 'GEPR-Directora', 'Laura Machava', 'Directora do Gabinete',
             'Solicitação do Plano de Actividades Conjuntas para 2026', '2026-01-15', 'Dir. Ortigio Nhanombe',
             'Dep. Planeamento Energético', 'Iazalde Jose Jeremias', None, 'Pendente', None),
            ('N/Refª80/ARENE-PCA/490/2025', 'ARENE', 'Paulo da Graça', 'PCA',
             'Estudo sobre a Política Tarifária para o Mercado Energético Nacional', '2025-01-23',
             'Dir. Marcelina Mataveia', 'Dep. Planeamento Energético', 'Iazalde Jose Jeremias',
             '2025-01-28', 'Dentro do Prazo', None),
            ('128/CA/310/2026', 'EDM', 'Joaquim Ou-Chim', 'PCA',
             'Agravamento das Penas Aplicáveis aos Crimes que Atentam Contra a Rede Eléctrica Nacional',
             '2026-04-11', 'Dir. Ortigio Nhanombe', 'Dep. Planeamento Energético',
             'Iazalde Jose Jeremias', None, 'Pendente',
             'Documento devolvido ao Director Nacional Adjunto para melhor enquadramento com os Juristas da DNE'),
        ]
        c.executemany(
            '''INSERT INTO documentos_recebidos
               (numero, proveniencia, remetente_nome, remetente_cargo, assunto, data_recepcao,
                despacho, endereçado_a, tecnico, data_resposta, prazo_status, observacao)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            records
        )

    def _load_initial_contactos(self, c):
        records = [
            (1, 'Dir. Marcelina Mataveia', 'mmataveia@yahoo.com', '824195400 / 840495452', 'Direcção', 'Directora'),
            (2, 'Dir. Ortigio Nhanombe', 'ortigiolois@gmail.com', '823959740', 'Direcção', 'Director'),
            (3, 'Iazalde Jose Jeremias', 'iazaldejose@gmail.com', '842821959', 'Dep. Planeamento Energético', 'Técnico'),
            (4, 'Estacio Chumbitico', 'estaciochumbitico@gmail.com', '840409362', 'Dep. Planeamento Energético', 'Técnico'),
            (5, 'Luis Guambe', 'luisguambe84@gmail.com', '848224897', 'Dep. Planeamento Energético', 'Técnico'),
            (6, 'Armindo Jone', 'armindojone@gmail.com', '846691153', 'Dep. Planeamento Energético', 'Técnico'),
            (7, 'Sergio Honwana', 'gabarsingue@gmail.com', '824099656', 'Dep. Planeamento Energético', 'Técnico'),
            (8, 'Anisio Pinto', 'anisiopintomanuel@gmail.com', '848576118', 'Dep. Planeamento Energético', 'Técnico'),
            (9, 'Bernardo Joao Nopia', 'nopiha20@yahoo.com.br', '848285831', 'Dep. Estudos e Projectos', 'Técnico'),
            (10, 'Francisco Mahangue', 'mahangue.fr@gmail.com', '842555253', 'Dep. Estudos e Projectos', 'Técnico'),
            (11, 'Manuel Andissene', 'manuelandissene@gmail.com', '829674910', 'Dep. Estudos e Projectos', 'Técnico'),
            (12, 'Rogerio Manhica', 'rogerio.manhica@gmail.com', '846733413', 'Dep. Licenciamento e Fiscalização', 'Técnico'),
            (13, 'Jose Mapilele', 'mapilas.ze@gmail.com', '843535174', 'Dep. Eficiência Energética', 'Técnico'),
            (14, 'Damiao Namuera', 'dnamuera@gmail.com', '824166198', 'Dep. Eficiência Energética', 'Técnico'),
            (15, 'Issufo Juma', 'issufojuma2003@yahoo.com.br', '845082416', 'Dep. Energias Renováveis', 'Técnico'),
            (16, 'Cristiano Gumete', 'cristianogumete@gmail.com', '843773052', 'Dep. Energias Renováveis', 'Técnico'),
            (17, 'Victoria Safrao', 'victoriasafrao@gmail.com', '845351745', 'Dep. Energias Renováveis', 'Técnico'),
            (18, 'Teresa Estevao', 'dne.mireme@mireme.gov.mz', '865611270', 'Rep. Administração e Finanças', 'Técnico'),
            (19, 'Benvinda Tembe', 'benvindateembe@gmail.com', '846582143', 'Rep. Administração e Finanças', 'Técnico'),
            (20, 'Susana Gomez', 'S.Gomez@institute.global', '845210770', 'Transição Energética', 'Técnico'),
            (21, 'Inocencio Gujamo', 'inocencio.gujamo@gmail.com', '844777042', 'UIPCE', 'Técnico'),
        ]
        c.executemany(
            'INSERT INTO contactos (numero, nome, email, telefone, departamento, cargo) VALUES (?,?,?,?,?,?)',
            records
        )

    # ---- Recebidos ----
    def get_all_recebidos(self, filters=None):
        conn = self.get_connection()
        c = conn.cursor()
        query = "SELECT * FROM documentos_recebidos WHERE 1=1"
        params = []
        if filters:
            if filters.get('search'):
                s = f"%{filters['search']}%"
                query += " AND (numero LIKE ? OR assunto LIKE ? OR remetente_nome LIKE ? OR proveniencia LIKE ?)"
                params += [s, s, s, s]
            if filters.get('tecnico'):
                query += " AND tecnico = ?"
                params.append(filters['tecnico'])
            if filters.get('prazo_status'):
                query += " AND prazo_status = ?"
                params.append(filters['prazo_status'])
            if filters.get('data_inicio'):
                query += " AND data_recepcao >= ?"
                params.append(filters['data_inicio'])
            if filters.get('data_fim'):
                query += " AND data_recepcao <= ?"
                params.append(filters['data_fim'])
        query += " ORDER BY data_recepcao DESC"
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_recebido(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM documentos_recebidos WHERE id=?", (id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def insert_recebido(self, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO documentos_recebidos
            (numero, proveniencia, remetente_nome, remetente_cargo, assunto, data_recepcao,
             despacho, endereçado_a, tecnico, data_resposta, prazo_status, observacao, ficheiro_path)
            VALUES (:numero, :proveniencia, :remetente_nome, :remetente_cargo, :assunto, :data_recepcao,
                    :despacho, :endereçado_a, :tecnico, :data_resposta, :prazo_status, :observacao, :ficheiro_path)''',
                  data)
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def update_recebido(self, id, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''UPDATE documentos_recebidos SET
            numero=:numero, proveniencia=:proveniencia, remetente_nome=:remetente_nome,
            remetente_cargo=:remetente_cargo, assunto=:assunto, data_recepcao=:data_recepcao,
            despacho=:despacho, endereçado_a=:endereçado_a, tecnico=:tecnico,
            data_resposta=:data_resposta, prazo_status=:prazo_status,
            observacao=:observacao, ficheiro_path=:ficheiro_path
            WHERE id=:id''',
                  {**data, 'id': id})
        conn.commit()
        conn.close()
        return True

    def delete_recebido(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM documentos_recebidos WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return True

    # ---- Enviados ----
    def get_all_enviados(self, filters=None):
        conn = self.get_connection()
        c = conn.cursor()
        query = "SELECT * FROM documentos_enviados WHERE 1=1"
        params = []
        if filters:
            if filters.get('search'):
                s = f"%{filters['search']}%"
                query += " AND (numero LIKE ? OR assunto LIKE ? OR destinatario_nome LIKE ? OR instituicao LIKE ?)"
                params += [s, s, s, s]
            if filters.get('assinante'):
                query += " AND assinante = ?"
                params.append(filters['assinante'])
            if filters.get('data_inicio'):
                query += " AND data_envio >= ?"
                params.append(filters['data_inicio'])
            if filters.get('data_fim'):
                query += " AND data_envio <= ?"
                params.append(filters['data_fim'])
        query += " ORDER BY data_envio DESC"
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_enviado(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM documentos_enviados WHERE id=?", (id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def insert_enviado(self, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO documentos_enviados
            (numero, assunto, preparado_por, assinante, destinatario_nome, destinatario_cargo,
             instituicao, data_envio, ficheiro_path, observacao)
            VALUES (:numero, :assunto, :preparado_por, :assinante, :destinatario_nome,
                    :destinatario_cargo, :instituicao, :data_envio, :ficheiro_path, :observacao)''',
                  data)
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def update_enviado(self, id, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''UPDATE documentos_enviados SET
            numero=:numero, assunto=:assunto, preparado_por=:preparado_por, assinante=:assinante,
            destinatario_nome=:destinatario_nome, destinatario_cargo=:destinatario_cargo,
            instituicao=:instituicao, data_envio=:data_envio, ficheiro_path=:ficheiro_path,
            observacao=:observacao WHERE id=:id''',
                  {**data, 'id': id})
        conn.commit()
        conn.close()
        return True

    def delete_enviado(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM documentos_enviados WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return True

    # ---- Reunioes ----
    def get_all_reunioes(self, filters=None):
        conn = self.get_connection()
        c = conn.cursor()
        query = "SELECT * FROM reunioes WHERE 1=1"
        params = []
        if filters:
            if filters.get('search'):
                s = f"%{filters['search']}%"
                query += " AND (assunto LIKE ? OR organizador LIKE ? OR num_doc LIKE ?)"
                params += [s, s, s]
            if filters.get('data_reuniao'):
                query += " AND data_reuniao = ?"
                params.append(filters['data_reuniao'])
        query += " ORDER BY data_reuniao ASC"
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_reuniao(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM reunioes WHERE id=?", (id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def insert_reuniao(self, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO reunioes
            (num_doc, organizador, data_convocatoria, assunto, data_reuniao, hora_local,
             link_convocatoria, participantes, contactos, decisoes, ficheiro_path)
            VALUES (:num_doc, :organizador, :data_convocatoria, :assunto, :data_reuniao,
                    :hora_local, :link_convocatoria, :participantes, :contactos, :decisoes, :ficheiro_path)''',
                  data)
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def update_reuniao(self, id, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''UPDATE reunioes SET
            num_doc=:num_doc, organizador=:organizador, data_convocatoria=:data_convocatoria,
            assunto=:assunto, data_reuniao=:data_reuniao, hora_local=:hora_local,
            link_convocatoria=:link_convocatoria, participantes=:participantes,
            contactos=:contactos, decisoes=:decisoes, ficheiro_path=:ficheiro_path
            WHERE id=:id''',
                  {**data, 'id': id})
        conn.commit()
        conn.close()
        return True

    def delete_reuniao(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM reunioes WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return True

    # ---- Contactos ----
    def get_all_contactos(self, search=None):
        conn = self.get_connection()
        c = conn.cursor()
        if search:
            s = f"%{search}%"
            c.execute("SELECT * FROM contactos WHERE nome LIKE ? OR departamento LIKE ? OR email LIKE ? ORDER BY numero",
                      (s, s, s))
        else:
            c.execute("SELECT * FROM contactos ORDER BY numero")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_contacto(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM contactos WHERE id=?", (id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def insert_contacto(self, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO contactos (numero, nome, email, telefone, departamento, cargo)
                     VALUES (:numero, :nome, :email, :telefone, :departamento, :cargo)''', data)
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return new_id

    def update_contacto(self, id, data):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''UPDATE contactos SET numero=:numero, nome=:nome, email=:email,
                     telefone=:telefone, departamento=:departamento, cargo=:cargo WHERE id=:id''',
                  {**data, 'id': id})
        conn.commit()
        conn.close()
        return True

    def delete_contacto(self, id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM contactos WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return True

    def get_nomes_contactos(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT nome FROM contactos ORDER BY nome")
        nomes = [r[0] for r in c.fetchall()]
        conn.close()
        return nomes

    # ---- Relatorio ----
    def get_anos_disponiveis(self):
        """Devolve lista de anos com documentos registados, ordenados DESC."""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""SELECT DISTINCT substr(data_recepcao, 1, 4) as ano
                     FROM documentos_recebidos WHERE data_recepcao IS NOT NULL AND data_recepcao != ''
                     UNION
                     SELECT DISTINCT substr(data_envio, 1, 4) as ano
                     FROM documentos_enviados WHERE data_envio IS NOT NULL AND data_envio != ''
                     ORDER BY ano DESC""")
        anos = [r[0] for r in c.fetchall() if r[0]]
        conn.close()
        ano_atual = str(date.today().year)
        if ano_atual not in anos:
            anos.insert(0, ano_atual)
        return anos

    def get_relatorio_stats(self, ano=None, mes=None):
        conn = self.get_connection()
        c = conn.cursor()
        ano = ano or str(date.today().year)

        # prefixo de data para filtro: "2026-03" (ano+mês) ou "2026" (só ano)
        if mes and mes != "0":
            prefixo_rec = f"{ano}-{int(mes):02d}"
            prefixo_env = prefixo_rec
            prefixo_reu = prefixo_rec
        else:
            prefixo_rec = ano
            prefixo_env = ano
            prefixo_reu = date.today().strftime('%Y-%m') if ano == str(date.today().year) else f"{ano}-01"

        c.execute("SELECT COUNT(*) FROM documentos_recebidos WHERE data_recepcao LIKE ?", (f"{prefixo_rec}%",))
        total_recebidos = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM documentos_recebidos
                     WHERE data_resposta IS NOT NULL AND data_resposta != ''
                     AND data_recepcao LIKE ?""", (f"{prefixo_rec}%",))
        total_respondidos = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM documentos_recebidos
                     WHERE prazo_status='Dentro do Prazo' AND data_recepcao LIKE ?""", (f"{prefixo_rec}%",))
        total_dentro = c.fetchone()[0]

        c.execute("""SELECT COUNT(*) FROM documentos_recebidos
                     WHERE prazo_status='Fora do Prazo' AND data_recepcao LIKE ?""", (f"{prefixo_rec}%",))
        total_fora = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM reunioes WHERE data_reuniao LIKE ?", (f"{prefixo_reu}%",))
        reunioes_mes = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM documentos_enviados WHERE data_envio LIKE ?", (f"{prefixo_env}%",))
        total_enviados = c.fetchone()[0]

        respondidos_com_status = total_dentro + total_fora
        taxa = round((total_dentro / respondidos_com_status * 100) if respondidos_com_status > 0 else 0, 1)

        conn.close()
        return {
            'total_recebidos': total_recebidos,
            'total_respondidos': total_respondidos,
            'taxa_cumprimento': taxa,
            'total_fora_prazo': total_fora,
            'reunioes_mes': reunioes_mes,
            'total_enviados': total_enviados,
        }

    def get_relatorio_departamentos(self, ano=None, mes=None):
        conn = self.get_connection()
        c = conn.cursor()
        ano = ano or str(date.today().year)
        if mes and mes != "0":
            prefixo = f"{ano}-{int(mes):02d}"
        else:
            prefixo = ano

        departamentos = [
            'Dep. Estudos e Projectos',
            'Dep. Licenciamento e Fiscalização',
            'Dep. Eficiência Energética',
            'Dep. Energias Renováveis',
            'Dep. Planeamento Energético',
            'Rep. Administração e Finanças',
        ]
        result = []
        for dep in departamentos:
            c.execute("SELECT COUNT(*) FROM documentos_recebidos WHERE endereçado_a=? AND data_recepcao LIKE ?", (dep, f"{prefixo}%"))
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM documentos_recebidos WHERE endereçado_a=? AND prazo_status='Dentro do Prazo' AND data_recepcao LIKE ?", (dep, f"{prefixo}%"))
            dentro = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM documentos_recebidos WHERE endereçado_a=? AND prazo_status='Fora do Prazo' AND data_recepcao LIKE ?", (dep, f"{prefixo}%"))
            fora = c.fetchone()[0]
            taxa = round((dentro / total * 100) if total > 0 else 0, 1)
            result.append({'departamento': dep, 'total': total, 'dentro_prazo': dentro, 'fora_prazo': fora, 'taxa': taxa})
        conn.close()
        return result

    def get_remetentes_frequentes(self, ano=None, mes=None):
        conn = self.get_connection()
        c = conn.cursor()
        ano = ano or str(date.today().year)
        if mes and mes != "0":
            prefixo = f"{ano}-{int(mes):02d}"
        else:
            prefixo = ano
        c.execute('''SELECT proveniencia, COUNT(*) as total
                     FROM documentos_recebidos
                     WHERE proveniencia IS NOT NULL AND proveniencia != ''
                     AND data_recepcao LIKE ?
                     GROUP BY proveniencia ORDER BY total DESC LIMIT 10''', (f"{prefixo}%",))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def check_alertas(self):
        conn = self.get_connection()
        c = conn.cursor()
        today = date.today().isoformat()

        c.execute('''SELECT id, numero, assunto, data_recepcao, tecnico FROM documentos_recebidos
                     WHERE (data_resposta IS NULL OR data_resposta = '')
                     AND prazo_status NOT IN ("Arquivado", "Fora do Prazo")''')
        pendentes = [dict(r) for r in c.fetchall()]

        from datetime import timedelta
        proximos_3 = (date.today() + timedelta(days=3)).isoformat()
        c.execute('''SELECT id, assunto, data_reuniao, hora_local, organizador FROM reunioes
                     WHERE data_reuniao >= ? AND data_reuniao <= ? ORDER BY data_reuniao''',
                  (today, proximos_3))
        reunioes = [dict(r) for r in c.fetchall()]
        conn.close()
        return {'docs_pendentes': pendentes, 'reunioes_proximas': reunioes}

    # ---- Exports ----
    def export_recebidos_excel(self, filepath, filters=None):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            rows = self.get_all_recebidos(filters)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Documentos Recebidos"
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill("solid", fgColor="1F4E79")
            headers = ['ID', 'Nº Documento', 'Proveniência', 'Remetente', 'Cargo', 'Assunto',
                       'Data Recepção', 'Despacho', 'Endereçado A', 'Técnico', 'Data Resposta',
                       'Status Prazo', 'Observação']
            ws.append(headers)
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            for r in rows:
                ws.append([r.get('id'), r.get('numero'), r.get('proveniencia'), r.get('remetente_nome'),
                            r.get('remetente_cargo'), r.get('assunto'), r.get('data_recepcao'),
                            r.get('despacho'), r.get('endereçado_a'), r.get('tecnico'),
                            r.get('data_resposta'), r.get('prazo_status'), r.get('observacao')])
            for col in ws.columns:
                max_len = max((len(str(cell.value or '')) for cell in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
            wb.save(filepath)
            return True
        except Exception as e:
            print(f"Erro ao exportar: {e}")
            return False

    def export_enviados_excel(self, filepath, filters=None):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            rows = self.get_all_enviados(filters)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Documentos Enviados"
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill("solid", fgColor="1F4E79")
            headers = ['ID', 'Nº Doc', 'Assunto', 'Preparado Por', 'Assinante',
                       'Destinatário', 'Cargo Dest.', 'Instituição', 'Data Envio', 'Observação']
            ws.append(headers)
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            for r in rows:
                ws.append([r.get('id'), r.get('numero'), r.get('assunto'), r.get('preparado_por'),
                            r.get('assinante'), r.get('destinatario_nome'), r.get('destinatario_cargo'),
                            r.get('instituicao'), r.get('data_envio'), r.get('observacao')])
            for col in ws.columns:
                max_len = max((len(str(cell.value or '')) for cell in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
            wb.save(filepath)
            return True
        except Exception as e:
            print(f"Erro ao exportar: {e}")
            return False

    def export_contactos_excel(self, filepath):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            rows = self.get_all_contactos()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Contactos"
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill("solid", fgColor="1F4E79")
            headers = ['Nº', 'Nome', 'Email', 'Telefone', 'Departamento', 'Cargo']
            ws.append(headers)
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            for r in rows:
                ws.append([r.get('numero'), r.get('nome'), r.get('email'),
                            r.get('telefone'), r.get('departamento'), r.get('cargo')])
            for col in ws.columns:
                max_len = max((len(str(cell.value or '')) for cell in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
            wb.save(filepath)
            return True
        except Exception as e:
            print(f"Erro ao exportar: {e}")
            return False
