import http.server
import socketserver
import sqlite3
import json
import time

from urllib.parse import unquote_plus


#
# Définition du nouveau handler
#
class RequestHandler(http.server.SimpleHTTPRequestHandler):

  # sous-répertoire racine des documents statiques
  static_dir = '/client'

  #
  # On surcharge la méthode qui traite les requêtes GET
  #
  def do_GET(self):
    self.init_params()

    # le chemin d'accès commence par /time
    if self.path.startswith('/time'):
      self.send_time()

    # On se débarasse une bonne fois pour toutes du cas favicon.ico
    elif len(self.path_info) > 0 and self.path_info[0] == 'favicon.ico':
      self.send_error(204)

    # le chemin d'accès commence par le nom de projet au pluriel
    elif len(self.path_info) > 0 and self.path_info[0] == entity_list_name:
      self.send_list()

    # le chemin d'accès commence par le nom du projet au singulier, suivi par un nom de lieu
    elif len(self.path_info) > 1 and self.path_info[0] == entity_name:
      self.send_data(self.path_info[1])
      
    elif len(self.path_info) > 1 and self.path_info[0] == 'commentaires':
        volcan = self.path_info[1]
        cur = conn.cursor()
        cur.execute("SELECT * FROM commentaires WHERE site ='" + volcan+"'")
        r = cur.fetchall()
        
        liste = []
        for i in range(len(r)) :
            liste.append({})
            for j in r[i].keys() :
                liste[i][j] = r[i][j]
        print(liste)
        self.send_json(liste)

    # ou pas...
    else:
      self.send_static()
      
      
  def do_POST(self):
      self.init_params()
#      print("a")
      if self.path_info[0] == "commentaire":
            print("a1")
            content_len = int(self.headers.get('Content-Length'))
            data = self.rfile.read(content_len)
            data = json.loads(data)
            cur = conn.cursor()
            cur.execute('SELECT * FROM utilisateurs WHERE pseudo = ?', (data['pseudo'],))
            utilisateur = cur.fetchone()
            if utilisateur:
                # l'utilisateur appartient à la bdd
                if data['password'] == utilisateur[2]:
                    # c'est le bon mot de passe
                    if '' in data.values() or len(data) < 5:
                        self.send_error(422, "La requête est incomplète")
                    else:
                        print("a2")
                        # on peut faire le commentaire
                        temps = int(time.time())
                        cur.execute("""INSERT INTO commentaires (pseudo, site, timestamp, message, date)
                                        VALUES (?, ?, ?, ?, ?)""", (data['pseudo'], data['site'], temps, data['message'], data['date'],))
                        conn.commit()
                        self.send_json({"pseudo":data['pseudo'], "site":data['site'], "timestamp":temps, "message":data['message'], "date":data['date']})
                else:
                    self.send_error(401, "Le mot de passe incorrect")
            else:
                self.send_error(401, "Le pseudo est introuvable")

          
  def do_DELETE(self):
      self.init_params()
      if len(self.path_info) > 1 and self.path_info[0] == 'commentaire':
            content_len = int(self.headers.get('Content-Length'))
            data = self.rfile.read(content_len)
            data = json.loads(data)
            cur = conn.cursor()
            cur.execute("SELECT * FROM commentaires WHERE id  ='" + self.path_info[1] +"'")
            r = cur.fetchone()
            cur = conn.cursor()
            cur.execute("SELECT * FROM utilisateurs WHERE pseudo  ='" + r['pseudo'] +"'")
            t = cur.fetchone()
            if r != [] :
                if data == None or t == None or data["password"] != t["Password"] :
                    self.send_error(401, 'Le mot de passe est incorrect')
                elif r == None or data["pseudo"] != r["pseudo"]:
                    self.send_error(401, "Le nom de l'utilisateur est incorrect")
                else :
                    cur.execute("DELETE FROM commentaires WHERE id =" + str(self.path_info[1]))
                    conn.commit()
                    self.send_response(204)
                    
                
                
  #
  # On surcharge la méthode qui traite les requêtes HEAD
  #
  def do_HEAD(self):
    self.send_static()

  #
  # On envoie le document statique demandé
  #
  def send_static(self):

    # on modifie le chemin d'accès en insérant un répertoire préfixe
    self.path = self.static_dir + self.path

    # on appelle la méthode parent (do_GET ou do_HEAD)
    # à partir du verbe HTTP (GET ou HEAD)
    if (self.command=='HEAD'):
        http.server.SimpleHTTPRequestHandler.do_HEAD(self)
    else:
        http.server.SimpleHTTPRequestHandler.do_GET(self)
        
    # # solution alternative plus élégante :
    # method = 'do_{}'.format(self.command)
    # getattr(http.server.SimpleHTTPRequestHandler,method)(self)


  #
  # On envoie un document avec l'heure
  #
  def send_time(self):
    
    # on récupère l'heure
    time = self.date_time_string()

    # on génère un document au format html
    body = '<!doctype html>' + \
           '<meta charset="utf-8">' + \
           '<title>l\'heure</title>' + \
           '<div>Voici l\'heure du serveur :</div>' + \
           '<pre>{}</pre>'.format(time)

    # pour prévenir qu'il s'agit d'une ressource au format html
    headers = [('Content-Type','text/html;charset=utf-8')]

    # on envoie
    self.send(body,headers)
    

  #
  # On envoie la liste des entités
  #
  def send_list(self):
  
    # on effectue une requête dans la base pour récupérer la liste des entités
    c = conn.cursor()
    c.execute("SELECT name, lat, lon FROM {}".format(entity_list_name))
    data = c.fetchall()

    # on construit la réponse en json
    body = json.dumps([dict(d) for d in data])
	
    # on envoie la réponse au client
    headers = [('Content-Type','application/json')]
    self.send(body,headers)


  #
  # On envoie les infos d'une entité
  #
  def send_data(self, name):

    # requête dans la base pour récupérer les infos de l'entité
    c = conn.cursor()
    c.execute("SELECT * FROM {} WHERE name=?".format(entity_list_name),(name,))
    r = c.fetchone()
	
    # construction de la réponse
    if r == None:
      self.send_error(404,'{} {} non trouvée'.format(entity_name,name))

    # on a trouvé l'item recherché
    else :
      info = { 'other': {} }

      # rangement des informations reçues
      for k in r.keys():
        if k == 'wiki' or k == 'photo' or k == 'abstract' :
          info[k] = r[k]
        elif '{}'.format(r[k]).startswith('http'):
          info['dbpedia'] = r[k]
        elif not k == 'name':
          info['other'][k] = r[k]

      # envoi de la réponse
      self.send_json(info)

  #
  # On envoie un document au format json
  #
  def send_json(self,data):
    headers = [('Content-Type','application/json')]
    self.send(json.dumps(data),headers)


  #
  # On envoie les entêtes et le corps fourni
  #
  def send(self,body,headers=[]):

    # on encode la chaine de caractères à envoyer
    encoded = bytes(body, 'UTF-8')

    # on envoie la ligne de statut
    self.send_response(200)

    # on envoie les lignes d'entête et la ligne vide
    [self.send_header(*t) for t in headers]
    self.send_header('Content-Length',int(len(encoded)))
    self.end_headers()

    # on envoie le corps de la réponse
    self.wfile.write(encoded)


  #
  # lecture des paramètres de la requête
  #
  def init_params(self):
    self.params = {}

    info = self.path.split('?',2)
    self.query_string = info[1] if len(info) > 1 else ''
    self.path_info = [unquote_plus(v) for v in info[0].split('/')[1:]]

    for c in self.query_string.split('&'):
      (k,v) = c.split('=',2) if '=' in c else ('',c)
      self.params[unquote_plus(k)] = unquote_plus(v)
	  
    print('path_info : {}'.format(self.path_info))
    print('params : {}'.format(self.params))
	  


#
# MODIFIER ICI EN FONCTION DU NOM DE VOTRE PROJET
#
# nom dese entités traitées par votre projet, au pluriel
entity_list_name = "volcans"


# on en déduit le nom des entités au singulier
entity_name = entity_list_name[:-1]

#
# Connexion à la base de données
# conn est une variable globale
#
dbname = '{}.db'.format(entity_list_name)
conn = sqlite3.connect(dbname)

# pour récupérer les résultats sous forme d'un dictionnaire
conn.row_factory = sqlite3.Row


#
# Instanciation et lancement du serveur
#
httpd = socketserver.TCPServer(("", 8080), RequestHandler)
httpd.serve_forever()
