import pandas as pd

def fatura_nubank(df):
    df.rename(columns={'title':'Despesa','amount':'Valor','date':'Data'},inplace=True)

    df['Tipo de Pagamento'] = 'Cartão de Crédito NUBANK'
    df['Tipo de Despesa'] = ''

    df['Pagamento'] = 'Á Vista'

    for idx, row in df.iterrows():
     if row['Valor'] < 0 :
        df.drop(idx,axis=0,inplace=True)

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
    fatura_c6.loc[0,'Pagamento'] = '5 de 12'
    fatura_c6.loc[1,'Pagamento'] = 'Á Vista'

    for idx, row in fatura_c6.iterrows():
     if row['Valor'] < 0 :
        fatura_c6.drop(idx,axis=0,inplace=True)

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
    df.drop(9,inplace=True)


    for idx, row in df.iterrows():
     if row['Valor'].find('-') >= 0 :
        df.drop(idx,axis=0,inplace=True)

    df['Valor'] = (df['Valor'].str.replace(',','.',regex=False).str.strip().astype(float))
    return df