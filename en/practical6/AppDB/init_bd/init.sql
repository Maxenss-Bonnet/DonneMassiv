CREATE TABLE IF NOT EXISTS livres (
    id SERIAL PRIMARY KEY,
    titre TEXT NOT NULL
);

INSERT INTO livres (titre) VALUES 
  ('Le Petit Prince'),
  ('1984'),
  ('L’Étranger');
