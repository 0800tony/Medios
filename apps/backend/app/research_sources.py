"""Fuentes permanentes que OLIVA puede consultar en investigación web.

Se cargan por usuario para que cada equipo pueda activarlas, desactivarlas o sumar
las propias. Una fuente es un filtro de investigación, no evidencia automática.
"""

from urllib.parse import urlparse


def domain_for(url: str) -> str:
    return urlparse(url).hostname.lower().removeprefix("www.")


DEFAULT_RESEARCH_SOURCES = [
    # Marketing, consumo e investigación global.
    ("Marketing Week", "https://www.marketingweek.com/", "Global", "marketing y consumo", "Estrategia de marca, efectividad y comportamiento del consumidor."),
    ("WARC", "https://www.warc.com/", "Global", "marketing y efectividad", "Casos, evidencia y mejores prácticas de marketing."),
    ("eMarketer", "https://www.emarketer.com/", "Global", "consumo y medios", "Datos sobre comercio, consumo, medios y comportamiento digital."),
    ("Think with Google", "https://www.thinkwithgoogle.com/", "Global", "consumo y efectividad", "Tendencias de búsqueda, consumo y efectividad."),
    ("NielsenIQ", "https://nielseniq.com/global/en/insights/", "Global", "retail e investigación", "Retail, FMCG, shoppers y medición de mercados."),
    ("Kantar", "https://www.kantar.com/inspiration", "Global", "investigación de mercados", "Marcas, consumidores, medios y creatividad."),
    ("Ipsos", "https://www.ipsos.com/en/insights", "Global", "investigación de mercados", "Opinión pública, tendencias sociales y comportamiento."),
    ("GWI", "https://www.gwi.com/blog", "Global", "audiencias digitales", "Audiencias y comportamiento digital global."),
    ("Mintel", "https://www.mintel.com/insights/", "Global", "tendencias de consumo", "Tendencias de consumo, innovación y categorías."),
    ("Euromonitor International", "https://www.euromonitor.com/insights", "Global", "mercados y categorías", "Mercados, categorías y tendencias globales."),
    ("TrendWatching", "https://www.trendwatching.com/", "Global", "tendencias", "Tendencias emergentes e innovación de consumo."),
    ("Trend Hunter", "https://www.trendhunter.com/", "Global", "tendencias", "Señales culturales, productos e innovación."),
    ("McKinsey Consumer Packaged Goods", "https://www.mckinsey.com/industries/consumer-packaged-goods/our-insights", "Global", "consumo y estrategia", "Estrategia y transformación en consumo masivo."),
    ("Bain Consumer Products", "https://www.bain.com/industry-expertise/consumer-products/", "Global", "consumo y estrategia", "Crecimiento, pricing y estrategia comercial."),
    ("Deloitte Consumer", "https://www.deloitte.com/global/en/Industries/consumer.html", "Global", "retail y consumo", "Estudios sobre retail y consumo."),
    ("NRF", "https://nrf.com/research-insights", "Global", "retail", "Investigación y tendencias del comercio minorista."),
    ("Retail Dive", "https://www.retaildive.com/", "Global", "retail", "Noticias y análisis de retail."),
    ("Consumer Goods Technology", "https://consumergoods.com/", "Global", "consumo y tecnología", "Tecnología y operación de marcas de consumo."),
    ("Harvard Business Review: Marketing", "https://hbr.org/topic/subject/marketing", "Global", "marketing y gestión", "Pensamiento estratégico y gestión de marketing."),
    ("American Marketing Association", "https://www.ama.org/", "Global", "marketing", "Conocimiento profesional y académico de marketing."),
    ("ESOMAR", "https://esomar.org/", "Global", "investigación de mercados", "Asociación mundial de investigación, datos e insights."),
    ("Research World", "https://researchworld.com/", "Global", "investigación de mercados", "Publicación del ecosistema de investigación e insights."),
    ("Greenbook", "https://www.greenbook.org/", "Global", "investigación de mercados", "Contenidos y directorio global de la industria."),
    ("Quirk’s Media", "https://www.quirks.com/", "Global", "investigación de mercados", "Métodos, casos, proveedores y recursos especializados."),
    ("Research Live", "https://www.research-live.com/", "Global", "investigación de mercados", "Noticias internacionales de investigación e insights."),
    ("Market Research Society", "https://www.mrs.org.uk/", "Global", "investigación de mercados", "Estándares, formación y recursos profesionales."),
    ("Insights Association", "https://www.insightsassociation.org/", "Global", "investigación de mercados", "Comunidad y regulación de la industria estadounidense."),
    ("AAPOR", "https://aapor.org/", "Global", "opinión pública", "Encuestas, opinión pública y calidad metodológica."),
    ("Pew Research Center", "https://www.pewresearch.org/", "Global", "investigación social", "Investigación social y opinión pública."),
    ("QRCA", "https://www.qrca.org/", "Global", "investigación cualitativa", "Investigación cualitativa y buenas prácticas."),
    ("Association for Qualitative Research", "https://www.aqr.org.uk/", "Global", "investigación cualitativa", "Recursos para investigación cualitativa."),
    ("YouGov", "https://yougov.com/", "Global", "audiencias y opinión", "Datos de opinión y perfiles de audiencias."),
    ("Qualtrics XM Institute", "https://www.qualtrics.com/xm-institute/", "Global", "experiencia de cliente", "Experiencia de cliente, empleado y marca."),
    ("Dynata", "https://www.dynata.com/resources/", "Global", "investigación de mercados", "Paneles, first-party data e investigación digital."),
    ("MarketResearch.com", "https://www.marketresearch.com/", "Global", "investigación de mercados", "Agregador de informes sectoriales."),
    ("Research and Markets", "https://www.researchandmarkets.com/", "Global", "investigación de mercados", "Catálogo internacional de estudios de mercado."),
    # Comunicación, creatividad y agencias globales.
    ("Adweek", "https://www.adweek.com/", "Global", "publicidad y agencias", "Marcas, creatividad, agencias, medios y tecnología."),
    ("Ad Age", "https://adage.com/", "Global", "publicidad y agencias", "Noticias y análisis de la industria publicitaria."),
    ("Campaign", "https://www.campaignlive.com/", "Global", "publicidad y agencias", "Creatividad, agencias, cuentas y talento."),
    ("The Drum", "https://www.thedrum.com/", "Global", "publicidad y agencias", "Marketing, medios y creatividad internacional."),
    ("Contagious", "https://www.contagious.com/", "Global", "creatividad", "Innovación creativa y análisis estratégico de campañas."),
    ("Shots", "https://www.shots.net/", "Global", "producción audiovisual", "Producción audiovisual y creatividad publicitaria."),
    ("LBBOnline", "https://www.lbbonline.com/", "Global", "publicidad y agencias", "Campañas, productoras, agencias y talento creativo."),
    ("Creative Review", "https://www.creativereview.co.uk/", "Global", "diseño y creatividad", "Diseño, comunicación visual y creatividad."),
    ("Ads of the World", "https://www.adsoftheworld.com/", "Global", "archivo creativo", "Archivo internacional de campañas."),
    ("Lürzer’s Archive", "https://www.luerzersarchive.com/", "Global", "archivo creativo", "Selección y archivo de creatividad mundial."),
    ("Reason Why", "https://www.reasonwhy.es/", "España", "publicidad y marketing", "Marketing y publicidad en español."),
    ("MarketingDirecto", "https://www.marketingdirecto.com/", "España", "publicidad y medios", "Actualidad publicitaria, medios y tecnología."),
    ("Digiday", "https://digiday.com/", "Global", "agencias y medios", "Transformación de agencias, medios y publicidad digital."),
    ("MediaPost", "https://www.mediapost.com/", "Global", "medios y planificación", "Medios, planificación, compra y tecnología publicitaria."),
    ("AdExchanger", "https://www.adexchanger.com/", "Global", "adtech", "Programática, datos, plataformas y adtech."),
    ("ExchangeWire", "https://www.exchangewire.com/", "Global", "adtech", "Publicidad digital y ecosistema tecnológico."),
    ("MarTech", "https://martech.org/", "Global", "tecnología de marketing", "Tecnología de marketing y operaciones."),
    ("AdForum", "https://www.adforum.com/", "Global", "agencias y creatividad", "Directorio mundial de agencias y archivo creativo."),
    ("Clutch", "https://clutch.co/agencies", "Global", "agencias", "Directorio de agencias basado en perfiles y reseñas."),
    ("Agency Spotter", "https://www.agencyspotter.com/", "Global", "agencias", "Búsqueda y comparación de agencias."),
    ("Sortlist", "https://www.sortlist.com/", "Global", "agencias", "Marketplace internacional de agencias."),
    ("DesignRush", "https://www.designrush.com/agency", "Global", "agencias", "Directorios y rankings de agencias."),
    ("Cannes Lions", "https://www.canneslions.com/", "Global", "festivales y creatividad", "Archivo y actualidad oficial de Cannes Lions."),
    ("D&AD", "https://www.dandad.org/", "Global", "festivales y creatividad", "Premios, casos y referentes de diseño y publicidad."),
    ("The One Club", "https://www.oneclub.org/", "Global", "festivales y creatividad", "The One Show, ADC y archivo creativo oficial."),
    ("Clio Awards", "https://clios.com/", "Global", "festivales y creatividad", "Premios y casos de comunicación y entretenimiento."),
    ("Effie Worldwide", "https://www.effie.org/", "Global", "efectividad", "Casos y criterios de efectividad de marketing."),
    # Argentina.
    ("Adlatina", "https://www.adlatina.com/", "Argentina", "publicidad y marketing", "Publicidad, marketing, agencias, campañas y medios latinoamericanos."),
    ("LatinSpots", "https://www.latinspots.com/", "Argentina", "creatividad", "Creatividad, campañas, agencias, productoras y festivales."),
    ("DossierNet / Carta de Publicidad", "https://dossiernet.com/", "Argentina", "publicidad y medios", "Marketing, publicidad, comunicación, agencias y medios."),
    ("TotalMedios", "https://www.totalmedios.com/", "Argentina", "medios y research", "Medios, publicidad, agencias, research, audiencias y tarifas."),
    ("Reporte Publicidad", "https://revistareporte.com.ar/", "Argentina", "publicidad", "Revista especializada en publicidad, marketing y comunicación."),
    ("Marketers by Adlatina", "https://www.marketersbyadlatina.com/", "Argentina", "marcas y consumo", "Gestión de marcas, anunciantes, consumo, liderazgo y estrategia."),
    ("Insider Latam", "https://insiderlatam.com/", "Argentina", "marketing e innovación", "Marketing, innovación, medios, plataformas, consumo y negocios latinoamericanos."),
    ("Mercado", "https://mercado.com.ar/", "Argentina", "negocios y marketing", "Empresas, marcas y consumidores."),
    ("El Ojo de Iberoamérica", "https://www.elojodeiberoamerica.com/", "Argentina", "creatividad y festivales", "Noticias, entrevistas, tendencias y casos iberoamericanos."),
    ("Infobrand", "https://www.infobrand.com.ar/", "Argentina", "branding", "Branding, identidad, marketing digital y gestión de marcas."),
    ("SAIMO", "https://saimo.org.ar/", "Argentina", "investigación de mercados", "Estudios sobre investigación de mercado, opinión pública e insights."),
    ("Market Knowledge Center", "https://www.marketknowledgecenter.com/", "Argentina", "investigación de mercados", "Investigaciones de mercado y opinión pública."),
    ("IAB Argentina", "https://www.iabargentina.com.ar/", "Argentina", "publicidad digital", "Informes de publicidad digital, audiencias y comercio electrónico."),
    ("Cámara Argentina de Anunciantes", "https://anunciantes.org.ar/", "Argentina", "anunciantes y medios", "Estudios sobre inversión publicitaria, marcas y consumidores."),
    # Uruguay.
    ("Revista Mercadeo", "https://adm.com.uy/revista-mercadeo/", "Uruguay", "marketing y negocios", "Marketing, empresas, comercio, tecnología e innovación."),
    ("IAB Uruguay", "https://www.iab.com.uy/", "Uruguay", "publicidad digital", "Estudios de publicidad digital, influencers, retail media y audiencias."),
    ("AUDAP", "https://audap.com.uy/", "Uruguay", "industria publicitaria", "Investigaciones de la industria publicitaria y su impacto económico."),
    ("Círculo Uruguayo de la Publicidad", "https://www.circulopublicidad.com/", "Uruguay", "creatividad y agencias", "Actualidad creativa, agencias, profesionales y premios."),
    ("InMediaciones de la Comunicación", "https://revistas.ort.edu.uy/inmediaciones-de-la-comunicacion/", "Uruguay", "comunicación y cultura", "Revista académica sobre comunicación, medios, tecnología, publicidad y cultura."),
]


def source_payload(row: tuple[str, str, str, str, str]) -> dict[str, str | int]:
    name, url, country, topic, description = row
    return {"name": name, "url": url, "domain": domain_for(url), "country": country, "topic": topic, "description": description, "priority": 1}
