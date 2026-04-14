from pathlib import Path
import re
import pandas as pd

categorias = {
'Alimentação':['comfrutas','amigao','panificadora'],
'Cabelereiro':['chies'],
'Cartão':[],
'Conhecimento':['asimov','unarrado','aprova total','estrategia','livro'],
'Diversos':['google one','notebook'],
'Farmácia':[],
'Igreja':[],
'Música':['música'],
'Plano Celular':['tim'],
'Presentes':[],
'Saúde':['h f','clinica''saúde','saude','treino','coluna','panobiancos'],
'Transporte':['partiu','postos','expresso','uber'],
}

def limpar_texto(texto):
    texto = texto.lower()
    texto = re.sub('[^a-zA-ZÀ-ÿ0-9 ]','',texto)
    texto = texto.strip()
    
    return texto

def mapa_despesas():
   caminho = Path.cwd() / 'csv'
   #data_frames = []

   for csv in caminho.glob('*.csv'):
      map_df = pd.read_csv(csv,encoding='utf-8',sep=',')
    
   return map_df