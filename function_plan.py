from fastapi import HTTPException

def check_limit(df, total_despesas, limite) :

    if (total_despesas + len(df) > limite):
        raise HTTPException(
            status_code=400,
            detail="Limite do Plano Gratuito Atingido"
        )
