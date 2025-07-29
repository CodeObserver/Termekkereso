from flask import Flask, render_template, request, jsonify
import requests
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

app = Flask(__name__)

# API függvények

def keres_termekek(termek):
    url = "https://arfigyelo.gvh.hu/api/search"
    params = {"q": termek, "limit": 20, "offset": 0, "order": "relevance"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("products", [])
    return []

def lekér_termek_adatok(termek_id):
    url = f"https://arfigyelo.gvh.hu/api/product/{termek_id}"
    return requests.get(url).json()

def varos_koordinatak(varos):
    geolocator = Nominatim(user_agent="termekkereso")
    location = geolocator.geocode(varos)
    return (location.latitude, location.longitude)

def metszet_boltlanclistak(termek_adatok_lista):
    kozos_lancok = None
    for termek_adat in termek_adatok_lista:
        láncok = set(lánc.get("uuid") for lánc in termek_adat.get("chainStores", []))
        kozos_lancok = láncok if kozos_lancok is None else kozos_lancok & láncok
    return kozos_lancok or set()


def top_kozeli_boltok(kozos_lancok, user_location, tavolsag):
    shops = requests.get("https://arfigyelo.gvh.hu/api/shops").json().get("shops", [])
    nearby = []
    for shop in shops:
        
            bolt_loc = (shop["location"]["latitude"], shop["location"]["longitude"])
            tav = geodesic(user_location, bolt_loc).km
            if tav<=tavolsag:
                nearby.append((tav, shop))
    nearby.sort()
    return nearby

def termek_mely_boltban(termek_adatok_lista):
    """
    Visszaad egy listát, ahol minden elem egy termékhez tartozó bolti UUID-k listája,
    ahol az adott termék elérhető.
    """
    boltokban = []
    for termek_adat in termek_adatok_lista:
        boltok_set = set()
        for chain in termek_adat.get("chainStores", []):
            # availableInShops egy lista bolt UUID-kkel
            boltok_set.update(chain.get("availableInShops", []))
        boltokban.append(boltok_set)
    return boltokban


def bolt_kosar_ara(bolt, termek_adatok_lista, boltok_per_termek=None):
    """
    Számolja a boltban elérhető termékek árainak összegét.
    A boltok_per_termek előre lekérhető a teljes lista alapján, hogy ne számoljuk újra.
    """
    if boltok_per_termek is None:
        boltok_per_termek = termek_mely_boltban(termek_adatok_lista)

    osszeg = 0
    bolt_uuid = bolt['uuid']
    bolt_chain_uuid = bolt.get('chainStoreUuid')

    for i, termek in enumerate(termek_adatok_lista):
        termek_ar = None
        for chain in termek.get("chainStores", []):
            if chain.get("uuid") == bolt_chain_uuid:
                if bolt_uuid in chain.get("availableInShops", []):
                    prices = chain.get("prices", [])
                    termek_ar=prices[0]['amount']
                    break
                

            
           

        # Csak akkor számoljuk hozzá az árat, ha a termék elérhető a boltban
        if termek_ar is not None:
            osszeg += termek_ar

    return round(osszeg, 2)


def mutat_terkep(dists,boltok, user_location, termek_adatok_lista, chain_name_map,osszegek,elerhetotermekeklista):
    import folium
    import os

    

    #icon_color = 'green' if elerhetotermekeklista[ciklus] == len(termek_adatok_lista) else 'orange'

        # Kép URL-je (helyi fájl vagy online kép URL)
    spar_image_url = "https://upload.wikimedia.org/wikipedia/commons/7/7c/Spar-logo.svg"  # Itt egy példa URL képhez
    dm_image_url="https://upload.wikimedia.org/wikipedia/commons/5/50/Dm_Logo.svg"
    lidl_image_url=r'https://upload.wikimedia.org/wikipedia/commons/archive/9/91/20230101153400%21Lidl-Logo.svg'
    Auchan_image_url=r'https://upload.wikimedia.org/wikipedia/fr/c/cd/Logo_Auchan_%282015%29.svg'
    tesco_image_url="https://upload.wikimedia.org/wikipedia/en/b/b0/Tesco_Logo.svg"
    rossman_image_url=r'https://upload.wikimedia.org/wikipedia/commons/8/8e/Rossmann_Logo.svg'
    penny_image_url=r'https://upload.wikimedia.org/wikipedia/commons/8/8e/Penny-Logo.svg'
    muller_image_url=r'https://upload.wikimedia.org/wikipedia/commons/e/e7/Mueller-logo.svg'
    aldi_iamge_url=r'https://upload.wikimedia.org/wikipedia/commons/6/64/AldiWorldwideLogo.svg'




    m = folium.Map(location=user_location, zoom_start=12)
    folium.Marker(user_location, tooltip="Keresési hely", icon=folium.Icon(color='blue')).add_to(m)
    ciklus=0
    for bolt in boltok:
        loc = (bolt['location']['latitude'], bolt['location']['longitude'])
        chain_name = chain_name_map.get(bolt.get("chainStoreUuid"), "Ismeretlen")

        
        
        # Kép beágyazása DivIcon-ban
        aruhaz=bolt.get('uuid').split('-')[0]

        if(aruhaz=="spar"):
            image_url=spar_image_url
        elif(aruhaz=="lidl"):
            image_url=lidl_image_url
        elif(aruhaz=="dm"):
            image_url=dm_image_url
        elif(aruhaz=="auchan"):
            image_url=Auchan_image_url
        elif(aruhaz=="tesco"):
            image_url=tesco_image_url
        elif(aruhaz=="rossman"):
            image_url=rossman_image_url
        elif(aruhaz=="penny"):
            image_url=penny_image_url
        elif(aruhaz=="mueller" ):
            image_url=muller_image_url
        elif(aruhaz=="aldi"):
            image_url=aldi_iamge_url

        if elerhetotermekeklista[ciklus] == len(termek_adatok_lista):
            if image_url!=lidl_image_url and image_url!=penny_image_url and image_url!=muller_image_url:
                icon = folium.DivIcon(html=f'<div style="display: inline-block; border-radius: 100%; box-shadow: 0 0 30px 10px rgba(0, 255, 255, 1);"> <img src="{image_url}" style="width: 45px; height: 45px; object-fit: contain;" /> </div>')
            else:
                icon = folium.DivIcon(html=f'<div style="display: inline-block; border-radius: 100%; box-shadow: 0 0 30px 10px rgba(0, 255, 255, 1);"> <img src="{image_url}" style="width: 60px; height: 60px; object-fit: contain;" /> </div>')
        else:
            if image_url!=lidl_image_url and image_url!=aldi_iamge_url and image_url!=penny_image_url and  image_url!=muller_image_url:
                
                icon = folium.DivIcon(html=f'<img src="{image_url}" width="15" height="15" />')
            else:
                icon = folium.DivIcon(html=f'<img src="{image_url}" width="33" height="33" />')

    
            
            

        popup_szoveg = f"<b>{aruhaz.upper()}</b><br><br>{bolt['city']}, {bolt['address']}<br><br>Végösszeg: {osszegek[ciklus]} Ft<br><br>Nyitvatartás: {bolt.get('openingTime')}<br><br>Elérhetőtermékek:{elerhetotermekeklista[ciklus]}"

        folium.Marker(
                loc,
                popup=popup_szoveg,
                tooltip=f"{chain_name} ({dists[ciklus]:.2f} km)",
                icon=icon
        ).add_to(m)
        ciklus+=1

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    filepath = os.path.join(static_dir, "bolt_terkep.html")
    m.save(filepath)
    return "bolt_terkep.html"


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/keres_termekek")
def termek_kereses():
    q = request.args.get("q", "")
    talalatok = keres_termekek(q)
    return jsonify(talalatok)

@app.route("/kereses", methods=["POST"])
def keres():
    adat = request.json
    varos = adat.get("varos")
    termekek = adat.get("termekek", [])
    maxboltszam=adat["max"]
    
    

    if not varos or not termekek:
        return jsonify({"hiba": "Hiányzó adatok"}), 400

    user_loc = varos_koordinatak(varos)

    termek_adatok_lista = []
    for termek in termekek:
        termek_adatok_lista.append(lekér_termek_adatok(termek))

    kozos_lancok = metszet_boltlanclistak(termek_adatok_lista)
    print(kozos_lancok)
    top_boltok = top_kozeli_boltok(kozos_lancok, user_loc, 50)

    chain_resp = requests.get("https://arfigyelo.gvh.hu/api/chainStores").json()
    chain_name_map = {c["uuid"]: c["name"] for c in chain_resp.get("chainStores", [])}

    eredmenyek = []
    osszegek=[]
    elerhetoermekeklista=[]
    boltoklista=[]
    dists=[]

    termekek = []

    for dist, bolt in top_boltok:
        elerhetoTermekek = 0
        
        for i, termek in enumerate(termek_adatok_lista):
            for chain in termek.get("chainStores", []):
                if chain.get("uuid") == bolt.get("chainStoreUuid"):
                    if bolt["uuid"] in chain.get("availableInShops", []):
                        termekek.append({
                            "nev": termek["name"],
                            "kep": termek["imageUrl"]
                        })
                        elerhetoTermekek += 1
                        break

        chain_name = chain_name_map.get(bolt.get("chainStoreUuid"), "Ismeretlen bolt")
        osszeg = bolt_kosar_ara(bolt, termek_adatok_lista)
        if elerhetoTermekek != 0:
            boltoklista.append(bolt)
            elerhetoermekeklista.append(elerhetoTermekek)
            osszegek.append(osszeg)
            dists.append(dist)

            
    # Az indexek és az értékek összekapcsolása tuple-ökkel
    combined = list(zip(dists, boltoklista, osszegek, elerhetoermekeklista))

    # A 'combined' lista indexeivel együtt rendezzük az adatokat az elérhető termékek szerint
    # sorted_combined[0] == (index, ('ertek2_val', 'ertek3_val', 'ertek4_val', 'elerheto_termekek_val'))
    sorted_combined = sorted(enumerate(combined), key=lambda x: x[1][3], reverse=True)
    
    
    
    dist_top = [i[1][0] for i in sorted_combined[:maxboltszam]]

   
    boltok_top = [i[1][1] for i in sorted_combined[:maxboltszam]]

    
    osszegek_top = [i[1][2] for i in sorted_combined[:maxboltszam]]

    elerheto_termekek_top = [i[1][3] for i in sorted_combined[:maxboltszam]]

    for i in range(maxboltszam):

        eredmenyek.append({
                "lanc": boltok_top[i].get("uuid"),
                "cim": f"{boltok_top[i]['city']}, {boltok_top[i]['address']}",
                "tavolsag": round(dist_top[i], 2),
                "ar": osszegek_top[i],
                "elerhetoTermekek": elerheto_termekek_top[i],
                "termekek": termekek[i]
            })

    



    terkep_html = mutat_terkep(dist_top,boltok_top, user_loc, termek_adatok_lista, chain_name_map,osszegek_top,elerheto_termekek_top)
    return jsonify({"boltlista": eredmenyek[:maxboltszam], "terkep": terkep_html})



if __name__ == "__main__":
    app.run(debug=True)


