-- Executado pelo Postgres só na primeira subida (quando o volume ainda está vazio).
CREATE TABLE IF NOT EXISTS conversoes (
    id          SERIAL PRIMARY KEY,
    celsius     DOUBLE PRECISION NOT NULL,
    fahrenheit  DOUBLE PRECISION NOT NULL,
    kelvin      DOUBLE PRECISION NOT NULL,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
