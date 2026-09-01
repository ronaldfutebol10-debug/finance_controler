from fastapi import FastAPI, UploadFile, File, Header, Body,HTTPException
import pandas as pd
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from functions import fatura_C6,fatura_nubank,fatura_xp
from pathlib import Path
from Categorizar import categorias, limpar_texto, mapa_despesas
from function_plan import check_limit
from database import supabase
import jwt
from jwt import PyJWKClient
from gotrue.types import AdminUserAttributes
from typing import Dict
from datetime import datetime, timezone
import os

app = FastAPI()
origins= ["https://webappfinance.vercel.app"]

@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return {}
app.add_middleware(CORSMiddleware,
                   allow_origins=origins,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )


SUPABASE_URL = os.environ.get("SUPABASE_URL")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL, cache_keys=True)

def id_user(authorization: str = Header(...)):
 
  if not authorization.startswith("Bearer "):
     raise HTTPException(status_code=401, detail='Token Inválido')
   
  token = authorization.split(" ")[1]

  print(jwt.get_unverified_header(token))

  try:
   signing_assinature_key = jwks_client.get_signing_key_from_jwt(token)


   payload = jwt.decode(
     token,
     algorithms=['HS256','RS256','P-256'],
     key=signing_assinature_key,
     audience='authenticated'
   )

  except jwt.PyJWKError :
    raise HTTPException(status_code=401, detail='Token inválido')

  user_id = payload.get("sub")

  if not user_id :
     raise HTTPException(status_code=401, detail='Token sem id de usuário')
 
  return user_id
 
@app.post("/upload")
async def upload_csv(file: UploadFile = File(...), authorization: str = Header(...)):
    
    if not file.filename.endswith(".csv"):
     return {"erro": "Arquivo inválido"}
    
    
    user_id = id_user(authorization)
    if not user_id :
      raise HTTPException(status_code=404, detail="Usuário não identificado")

    usuário = supabase.table("usuários").select("limites_despesas").eq("id",user_id).single().execute()

    limite = usuário.data["limites_despesas"]

    total = supabase.table("despesas_pessoais").select("*",count="exact").eq("id_user",user_id).execute()

    total_despesas = total.count

    name = file.filename.upper()
    
    if 'NUBANK' in name:
      df = pd.read_csv(file.file,encoding='latin-1',sep=',')

      check_limit(df, total_despesas, limite)

      df = fatura_nubank(df)
      df['Data'] = pd.to_datetime(df['Data'])

    elif 'XP' in name :
     df = pd.read_csv(file.file,encoding='utf-8',sep=';')

     check_limit(df, total_despesas, limite)

     df = fatura_xp(df)
     df['Data'] = pd.to_datetime(df['Data'],format='%d/%m/%Y')

    elif 'C6' in name:
      df = pd.read_csv(file.file,encoding='utf-8',sep=';')
       
      check_limit(df, total_despesas, limite)

      df = fatura_C6(df)
      df['Data'] = pd.to_datetime(df['Data'],format='%d/%m/%Y')

    meses = {
    1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
    7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'
    }
    
    df['Mês de Compra'] = df['Data'].dt.month.map(meses)

    map_df = mapa_despesas()
    mapa_global = {
        limpar_texto(despesa): categoria 
        for despesa, categoria  in (zip(map_df['Despesa'],map_df['Tipo de Despesa']))}

    historico_categorias = supabase.table("mapa_despesa_usuario").select("despesa_limpa, tipo_despesa").eq("id_user", user_id).execute()
    mapa_historico = { despesa["despesa_limpa"] : despesa["tipo_despesa"] for despesa in historico_categorias.data }

    def categorizar_despesas(despesa):
        despesa = str(despesa)
        despesa = limpar_texto(despesa)

        if despesa in mapa_historico:
           return mapa_historico[despesa]

        if despesa in mapa_global :
            return mapa_global[despesa]

        for categoria, tipos in categorias.items():
            for tipo in tipos:
                if tipo in despesa:
                    return categoria
                
        return 'Diversos'

    df['Tipo de Despesa'] = df['Despesa'].apply(categorizar_despesas)
    df = df.dropna()
    df['Valor'] = (df['Valor']
                        .astype(str)
                        .str.replace(',','.',regex=False)
                        .str.strip()
                        .astype(float)
                        )
    
    df['Data'] = df['Data'].dt.strftime("%Y-%m-%d")
    df.columns = df.columns.str.lower().str.strip()
    df['ano de compra'] = datetime.now().year

    df = df.rename(columns={'tipo de despesa':'tipo_despesa','tipo de pagamento':'tipo_pagamento','ano de compra':'ano_de_compra','mês de compra':'mês_de_compra'})
    df['id_user'] = user_id


    dados = df.to_dict(orient="records")
    
    response = supabase.table('despesas_pessoais').insert(dados).execute()

    if response.data is None :
       raise HTTPException(status_code=500, detail="Erro ao inserir despesas da fatura no banco")
    
    return {"Status":"Dados importados e salvos com sucesso",
            "dados": dados, 
            "total_registros": len(df),
   }
   

@app.post("/despesa")
async def add_despesa(authorization : str = Header(...), despesa : dict = Body(...)):
        user_id = id_user(authorization)

        if not user_id :
         raise HTTPException(status_code=404, detail="Usuário não identificado")
        
        despesa['id_user'] = user_id

        usuário = supabase.table("usuários").select("limites_despesas").eq("id",user_id).single().execute()

        limite = usuário.data["limites_despesas"]

        total = supabase.table("despesas_pessoais").select("*",count="exact").eq("id_user",user_id).execute()

        total_despesas = total.count

        if total_despesas >= limite :
           raise HTTPException(
              status_code=403,
              detail="Limite do Plano Gratuito Atingido"
           )

        response = supabase.table('despesas_pessoais').insert([despesa]).execute()

        return {"data":response.data}


@app.get("/dados_despesas")
def dados_despesas(authorization : str = Header(...)):
    user_id = id_user(authorization)

    if not user_id :
      raise HTTPException(status_code=404, detail="Usuário não identificado")

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

   usuário = supabase.table("usuários").select("*").eq("id",user.id).execute()

   if not usuário.data:
       supabase.table("usuários").insert({
          "id":user.id,
          "email":user.email,
          "plano" : "free",
          "limites_despesas":30
       }).execute()

   return {
      'access_token': token,
      'user' : {
         "id":user.id,
         "email": user.email,
      }}
 
 except Exception as e:
    return {"erro":str(e)}

class DeletedDespesa(BaseModel):
   ids : list[str]
   
@app.delete("/delete_despesa")
async def delete_despesa(data: DeletedDespesa, authorization : str = Header(...)):


   user_id = id_user(authorization)
   if not user_id :
            raise HTTPException(status_code=404, detail="Usuário não identificado")
   
   ids = data.ids

   response = supabase.table('despesas_pessoais').delete().in_('id',ids).eq('id_user',user_id).execute()

   if not response.data:
      raise HTTPException(status_code=404,detail='Despesa não encontrada no banco de dados')

   return {'Data':response.data,
                'Quantidade de Despesas deletadas': len(response.data)
                }

@app.put("/update_despesa")
async def update_despesa(authorization : str = Header(...), despesa : dict = Body(...)):

      user_id = id_user(authorization)
      if not user_id :
         raise HTTPException(status_code=404, detail="Usuário não identificado")
      
      id_despesa = despesa.get("id")
      if not id_despesa:
         raise HTTPException(
            status_code=400,
            detail="ID da despesa não enviado"
      )
      despesa['id_user'] = user_id

      print("USER_ID:",user_id)
      print("DESPESA:",despesa)

      
      id_despesa = despesa.pop("id")

      response = supabase.table("despesas_pessoais").update(despesa).eq("id",id_despesa).eq("id_user",user_id).execute()

      if despesa.get("despesa") and despesa.get("tipo_despesa") :
         check = limpar_texto(despesa["despesa"])
         if check :
            supabase.table("mapa_despesas_usuario").upsert({
               "id_user" : user_id,
               "despesa_limpa" : check,
               "tipo_despesa" : despesa["tipo_despesa"],
               "date_update" : datetime.now(timezone.utc).isoformat()
            }, 
            on_conflict="id_user, despesa_limpa").execute()      


      return {
            "data":response.data}

@app.get("/dados_plano")
async def get_plano(authorization : str = Header(...)):
   user_id = id_user(authorization)

   if not user_id :
      raise HTTPException(
         status_code=404,
         detail="Usuário não cadastrado!"
      )

   plano_user = supabase.table("usuários").select("plano, nome").eq("id",user_id).single().execute()

   print("Nome", plano_user.data["nome"])
   print("Plano", plano_user.data["plano"])

   return {"plano": plano_user.data["plano"],
           "nome": plano_user.data["nome"]}

@app.post("/recuperar_senha")
async def recuperar_senha(email : str = Body(..., embed=True)):


   row = supabase.table("usuários").select("email").eq("email", email).execute()

   if not row.data:
      raise HTTPException(
         status_code=404,
         detail="Email não encontrado"
      )
   
   supabase.auth.reset_password_email(email=email)

   return {"Status":"Senha de recuperação enviada"}


@app.post("/auth/reset")
async def auth_user(authorization : str = Header(...), novaSenha : str = Body(...,embed=True)):

   id = id_user(authorization)

   print("ID usuário", id)
   print("Nova Senha recebida")

   response = supabase.auth.admin.update_user_by_id(
      uid=id,
      attributes=AdminUserAttributes(password=novaSenha)
   )

   if not response.user :
      raise HTTPException(
         status_code=404,
         detail="ID ou Senha inválida"
      )

   return {"Mensagem": "Senha atualizada com sucesso!",
           "Status": True }


@app.delete('/delete_meta/{id}')
async def deletar_meta(id : str, authorization : str = Header(...)) :
   id_auth = id_user(authorization)

   if not id_auth :
      raise HTTPException(status_code=404, detail='Usuário não encontrado')

   response = supabase.table("metas_gastos").delete().eq('id', id).eq("id_user", id_auth).execute()

   if not response.data :
      raise HTTPException (status_code=404, detail="Meta não encontrada na tabela")

   return {
      "status" : "Meta deletada com sucesso",
      "detail" : response.data
   }

@app.get("/dados_metas")
async def get_metas(authorization : str = Header(...)):

   id = id_user(authorization)

   if not id :
      raise HTTPException(status_code=404, detail="Usuário inválido")

   response = supabase.table('metas_gastos').select('*').eq("id_user", id).execute()

   if not response.data :
      raise HTTPException(status_code=500, detail="Erro ao consultar metas na tabela")

   print(response.data)

   return {
      "metas" : response.data
   }

class DadosMetas(BaseModel):
   valor_meta : int
   ano : int
   mes : str
   data_meta : str


@app.post('/add_meta')
async def add_meta(authorization : str = Header(...), dados_meta : DadosMetas = Body(...)):
   id = id_user(authorization)

   if not id : 
      raise HTTPException(status_code=500, detail="Usuário Inválido")

   dados = {
      "id_user" : id,
      "mes" : dados_meta.mes,
      "valor_meta" : dados_meta.valor_meta,
      "data_criacao" : dados_meta.data_meta,
      "ano" :dados_meta.ano
   }

   response = supabase.table("metas_gastos").upsert(dados,on_conflict="id_user, ano, mes").execute()

   if not response.data :
         raise HTTPException(status_code=500, detail="Erro ao inserir meta na tabela")

   return 'Meta Inserida com Sucesso'
