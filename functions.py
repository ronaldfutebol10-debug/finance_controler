import pandas as pd

def fatura_nubank(df):
    df.rename(columns={'title':'Despesa','amount':'Valor','date':'Data'},inplace=True)

    df['Tipo de Pagamento'] = 'Cartão de Crédito NUBANK'
    df['Tipo de Despesa'] = ''

    df['Pagamento'] = 'Á Vista'

    for idx, row in df.iterrows():
  
     if row['Valor'].startswith("-") :
      df.drop(idx,axis=0,inplace=True)

     if "." in row['Valor'] :
      df.loc[idx,'Valor'] = row['Valor'].replace(".","")
     
    return df[['Data'] + ['Tipo de Pagamento'] + ['Despesa'] + ['Tipo de Despesa'] + ['Valor'] + ['Pagamento']]

def fatura_C6(df):
    fatura_c6 = df.drop(labels=['Nome no Cartão','Final do Cartão','Categoria','Valor (em US$)','Cotação (em R$)'],axis=1)
    fatura_c6.rename(columns=
                     {'Data de Compra':'Data',
                      'Parcela':'Pagamento',
                      'Valor (em R$)':'Valor',
                      'Descrição':'Despesa'},
                     inplace=True)

    fatura_c6['Tipo de Pagamento'] = 'Cartão de Crédito C6'
    fatura_c6['Tipo de Despesa'] = ''

    fatura_c6['Valor'] = (fatura_c6['Valor'].astype(float))
    
    fatura_c6 = fatura_c6[fatura_c6['Valor'] >= 0]

    return fatura_c6[['Data'] + ['Tipo de Pagamento'] + ['Despesa'] + ['Tipo de Despesa'] + ['Valor'] + ['Pagamento']]

def fatura_xp(df):

    df.drop(labels=['Portador'],inplace=True,axis=1)
    df.rename(columns={'Estabelecimento':'Despesa','Parcela':'Pagamento'},inplace=True)

    df['Tipo de Pagamento'] = 'Cartão de Crédito XP'
    df['Tipo de Despesa'] = ''

    df = df[['Data'] + ['Tipo de Pagamento'] + ['Despesa'] + ['Tipo de Despesa'] + ['Valor'] + ['Pagamento']]

    df.loc[df['Pagamento'] == '-','Pagamento'] = 'Á Vista'

    valores = df['Valor'].values
    valores_formatados_xp = []

    for valor in valores:
        valor = valor.strip('R$')
        valores_formatados_xp.append(valor)

    df['Valor'] = valores_formatados_xp
    
    df['Valor'] = (df['Valor'].str.replace(',','.',regex=False).str.strip().astype(float))
    df = df[df['Valor'] >= 0]

    return df