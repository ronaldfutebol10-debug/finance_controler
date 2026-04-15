from fastapi import FastAPI, UploadFile, File, Header, Body,HTTPException
import pandas as pd
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from functions import fatura_C6,fatura_nubank,fatura_xp
from pathlib import Path
from Categorizar import categorias, limpar_texto, mapa_despesas
from database import supabase
from jose import jwt

SUPABASE_JWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzZXdnb2t0a251ZHJhc2R4cnZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTUwNDM1NCwiZXhwIjoyMDkxMDgwMzU0fQ.LYcqafXIYJ1wWTM_Woet1NfzcuXYbB_MrLV33e056CE'
app = FastAPI()
origins = ["https://finance-pessoal.up.railway.app"]

@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return {}
app.add_middleware(CORSMiddleware,
                   allow_origins=origins,
                   allow_origin_regex=r"https://.*\.lovable\.app", 
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )

def id_user(authorization: str = Header(...)):
 try:
  if not authorization.startswith("Bearer "):
     raise HTTPException(status_code=401, detail='Token Inválido')
    

  token = authorization.split(" ")[1]
  payload = jwt.decode(
     token,
     key="",
     options={"verify_signature": False,
              "verify_aud":False}
     )
  return payload.get("sub")
 except Exception as erro :
    raise Exception(f"Erro ao decodificar token -> {str(erro)}")
 

@app.get("/teste")
def teste():
    return {"ok": True}

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...),authorization: str = Header(...)):
    if not file.filename.endswith(".csv"):
     return {"erro": "Arquivo inválido"}
    
    user_id = id_user(authorization)
    name = file.filename.upper()

    
    if 'NUBANK' in name:
        df = pd.read_csv(file.file,encoding='latin-1',sep=',')

    elif 'XP' in name or 'C6' in name:
     df = pd.read_csv(file.file,encoding='utf-8',sep=';')

   

    if 'NUBANK' in name:
        df = fatura_nubank(df)
        df['Data'] = pd.to_datetime(df['Data'])

    if 'XP' in name:
        df = fatura_xp(df)
        df['Data'] = pd.to_datetime(df['Data'],format='%d/%m/%Y')
    
    if 'C6' in name:
        df = fatura_C6(df)
        df['Data'] = pd.to_datetime(df['Data'])


    meses = {
    1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
    7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'
    }
    df['Ano de Compra'] = df['Data'].dt.year
    df['Mês de Compra'] = df['Data'].dt.month.map(meses)

    map_df = mapa_despesas()
    mapa = {
        limpar_texto(despesa): categoria 
        for despesa, categoria  in (zip(map_df['Despesa'],map_df['Tipo de Despesa']))}
    
    def categorizar_despesas(despesa):
        despesa = limpar_texto(despesa)

        if despesa in mapa :
            return mapa[despesa]

        for categoria, tipos in categorias.items():
            for tipo in tipos:
                if tipo in despesa:
                    return categoria
                
        return 'Diversos'

    df['Tipo de Despesa'] = df['Despesa'].apply(categorizar_despesas)
    df['Valor'] = (df['Valor']
                        .astype(str)
                        .str.replace(',','.',regex=False)
                        .str.strip()
                        .astype(float)
                        )
    
    df['Data'] = df['Data'].dt.strftime("%Y-%m-%d")
    df.columns = df.columns.str.lower().str.strip()

    df = df.rename(columns={'tipo de despesa':'tipo_despesa','tipo de pagamento':'tipo_pagamento','ano de compra':'ano_de_compra','mês de compra':'mês_de_compra'})
    df['id_user'] = user_id

    dados = df.to_dict(orient="records")
    
    response = supabase.table('despesas_pessoais').insert(dados).execute()
    
    return {"Status":"Dados importados e salvos com sucesso",
            "dados": dados, 
            "total_registros": len(df)
            }

@app.post("/despesa")
async def add_despesa(authorization : str = Header(...), despesa : dict = Body(...)):
    try :
        user_id = id_user(authorization)
        despesa['id_user'] = user_id
        
        df_despesa = pd.DataFrame.from_dict(despesa,orient='index')

        df_despesa.reset_index().drop('index',axis=1,inplace=True)

        data_despesa = df_despesa.to_dict(orient='records')

        print("USER ID:", user_id)
        print('DESPESA:', despesa)


        response = supabase.table('despesas_pessoais').insert(data_despesa).execute()

        print("RESPONSE:", response)
        return {"ok":True,
                "data":response.data}
    except Exception as e :
        return {"erro":str(e)}

@app.get("/dados_despesas")
def dados_despesas(authorization : str = Header(...)):
    user_id = id_user(authorization)

    print("USER ID:", user_id)

    response = supabase.table('despesas_pessoais').select("*").eq("id_user",user_id).execute()

    print("DATA:", response)

    return response.data

@app.post("/login")
def login(data : dict = Body(...)):
 try:
   email = data.get('email')
   senha = data.get('password')
   
   response = supabase.auth.sign_in_with_password({
      "email" : email,
      "password" : senha
   })

   token = response.session.access_token
   user = response.user

   return {
      'access_token': token,
      'user' : {
         "id":user.id,
         "email": user.email,
      }}
 except Exception as e:
    return {"erro":str(e)}

