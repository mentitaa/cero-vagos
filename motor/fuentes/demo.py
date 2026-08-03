"""
Fuente de demostración: avisos de ejemplo escritos como los publican de verdad
los portales peruanos, con su HTML sucio incluido.

Sirve para dos cosas:
  1. Correr el motor completo sin tocar internet.
  2. Tener casos de prueba realistas del filtro (hay avisos que deben pasar y
     avisos que deben ser rechazados).
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

from ..modelos import OfertaCruda
from .base import Fuente


def _hace(dias: int) -> date:
    return date.today() - timedelta(days=dias)


AVISOS: list[dict] = [
    # ---------------------------------------------------------------- PASA
    {
        "fuente": "Computrabajo", "dias": 0,
        "puesto": "Asistente Contable", "empresa": "Grupo Ferreycorp",
        "ubicacion": "San Isidro, Lima",
        "sueldo_texto": "S/ 2,800 a S/ 3,400 mensuales",
        "html": """
        <p>Importante empresa del rubro de maquinaria pesada requiere Asistente Contable
        para apoyar en el cierre contable mensual de la unidad minera.</p>
        <p><b>Funciones:</b></p>
        <ul>
          <li>Registrar comprobantes de compra y venta en el sistema SAP</li>
          <li>Elaborar las conciliaciones bancarias mensuales de 6 cuentas</li>
          <li>Preparar los reportes de detracciones y percepciones para SUNAT</li>
          <li>Apoyar en el cierre contable mensual y anual del área</li>
          <li>Atender los requerimientos de la auditoría externa</li>
        </ul>
        <p><b>Requisitos:</b></p>
        <ul>
          <li>Bachiller o titulado en Contabilidad</li>
          <li>De 1 a 2 años de experiencia en puestos contables similares</li>
          <li>Excel intermedio (tablas dinámicas, BUSCARV)</li>
          <li>Deseable manejo del módulo SAP FI</li>
        </ul>
        <p><b>Beneficios:</b></p>
        <ul>
          <li>Ingreso a planilla con todos los beneficios de ley</li>
          <li>Modalidad híbrida: 3 días en oficina y 2 remotos</li>
          <li>EPS familiar cubierta al 60%</li>
          <li>Movilidad y almuerzo subvencionado</li>
          <li>Línea de carrera al puesto de Analista Contable</li>
        </ul>""",
    },
    {
        "fuente": "Web de la empresa", "dias": 1,
        "puesto": "Desarrollador Backend Node.js", "empresa": "Rappi Perú",
        "ubicacion": "Lima (100% remoto)",
        "sueldo_texto": "S/7000 - S/9500",
        "html": """
        <p>Buscamos un desarrollador backend para el squad de pagos, que atiende
        Perú y Chile.</p>
        <p>Responsabilidades</p>
        <ul>
          <li>Desarrollar y mantener microservicios en Node.js y TypeScript</li>
          <li>Diseñar endpoints REST y documentarlos en Swagger</li>
          <li>Optimizar consultas en PostgreSQL y cachés en Redis</li>
          <li>Participar en code reviews y en el on-call rotativo</li>
          <li>Escribir pruebas unitarias con Jest con cobertura mínima de 70%</li>
        </ul>
        <p>Requisitos</p>
        <ul>
          <li>3+ años de experiencia en desarrollo backend con Node.js</li>
          <li>Manejo de PostgreSQL, Docker y AWS (ECS o Lambda)</li>
          <li>Inglés intermedio para documentación y reuniones</li>
          <li>Egresado de Ingeniería de Sistemas, Informática o afines</li>
        </ul>
        <p>Qué ofrecemos</p>
        <ul>
          <li>Planilla completa desde el día 1 y EPS cubierta al 70%</li>
          <li>Trabajo 100% remoto desde cualquier ciudad del Perú</li>
          <li>Bono anual por desempeño de hasta 2 sueldos</li>
          <li>S/ 300 mensuales para internet y coworking</li>
          <li>20 días de vacaciones más tu cumpleaños libre</li>
        </ul>""",
    },
    {
        "fuente": "Bumeran", "dias": 2,
        "puesto": "Ejecutivo Comercial B2B", "empresa": "Alicorp",
        "ubicacion": "Arequipa, Arequipa",
        "sueldo_texto": "Desde S/ 3,500 más comisiones",
        "html": """
        <p>Gestión de cartera de bodegas y mayoristas en la zona sur del país.</p>
        <p>Actividades a realizar</p>
        <ul>
          <li>Gestionar una cartera de 80 clientes mayoristas en Arequipa</li>
          <li>Cumplir la cuota mensual de venta y de cobertura asignada</li>
          <li>Negociar espacios y exhibiciones en el punto de venta</li>
          <li>Reportar diariamente en el CRM las visitas realizadas</li>
          <li>Levantar información de precios de la competencia</li>
        </ul>
        <p>Perfil requerido</p>
        <ul>
          <li>2 años de experiencia en ventas de consumo masivo</li>
          <li>Licencia de conducir A-I vigente</li>
          <li>Disponibilidad para viajar dentro de la región sur</li>
          <li>Estudios técnicos o universitarios en Administración o Marketing</li>
        </ul>
        <p>Te ofrecemos</p>
        <ul>
          <li>Sueldo base de S/ 3,500 más comisiones sin tope</li>
          <li>Movilidad propia de la empresa y combustible cubierto</li>
          <li>Planilla, EPS y seguro de vida ley</li>
          <li>Bono trimestral por cumplimiento de cuota</li>
        </ul>""",
    },
    {
        "fuente": "Laborum", "dias": 3,
        "puesto": "Practicante de Marketing Digital", "empresa": "Cineplanet",
        "ubicacion": "Surco, Lima",
        "sueldo_texto": "Subvención de S/ 1,400",
        "html": """
        <p>Apoyo en la ejecución de campañas de redes sociales y email marketing
        para los estrenos del mes.</p>
        <p>¿Qué harás?</p>
        <ul>
          <li>Programar publicaciones en Instagram, TikTok y Facebook</li>
          <li>Redactar copies cortos para las campañas de estrenos</li>
          <li>Elaborar reportes semanales de métricas en Looker Studio</li>
          <li>Coordinar con la agencia creativa la entrega de piezas</li>
        </ul>
        <p>Requisitos</p>
        <ul>
          <li>Estudiante de últimos ciclos de Marketing, Comunicaciones o Publicidad</li>
          <li>Carta de presentación de la universidad para práctica pre-profesional</li>
          <li>Manejo de Canva y Meta Business Suite</li>
          <li>Disponibilidad de 30 horas semanales</li>
        </ul>
        <p>Beneficios</p>
        <ul>
          <li>Subvención de S/ 1,400 mensuales</li>
          <li>Modalidad híbrida, 3 días en oficina</li>
          <li>Entradas de cine gratis al mes para ti y un acompañante</li>
          <li>Horario flexible compatible con tus clases</li>
        </ul>""",
    },
    {
        "fuente": "Laborum", "dias": 1,
        "puesto": "Supervisor de Almacén", "empresa": "Ransa",
        "ubicacion": "Callao",
        "sueldo_texto": "S/ 3.800,00 - S/ 4.500,00 al mes",
        "html": """
        <p>Supervisión de las operaciones de recepción, picking y despacho del
        centro de distribución del Callao.</p>
        <p>Funciones principales:</p>
        <ul>
          <li>Supervisar a un equipo de 18 operarios por turno</li>
          <li>Controlar los indicadores de exactitud de inventario y fill rate</li>
          <li>Gestionar la recepción y el despacho de mercadería</li>
          <li>Asegurar el cumplimiento de las normas de seguridad y salud (SST)</li>
          <li>Elaborar los reportes diarios de productividad en el WMS</li>
        </ul>
        <p>Requisitos:</p>
        <ul>
          <li>3 años de experiencia supervisando operaciones logísticas</li>
          <li>Manejo de sistemas WMS y Excel intermedio</li>
          <li>Titulado o bachiller en Ingeniería Industrial o Logística</li>
          <li>Disponibilidad para turnos rotativos</li>
        </ul>
        <p>Condiciones laborales:</p>
        <ul>
          <li>Planilla completa desde el primer día</li>
          <li>Movilidad de acercamiento desde puntos de Lima</li>
          <li>Comedor en planta con almuerzo subvencionado</li>
          <li>Seguro de vida ley y EPS opcional</li>
        </ul>""",
    },

    # ------------------------------------------------------------ RECHAZOS
    {   # sin sueldo declarado
        "fuente": "Computrabajo", "dias": 0,
        "puesto": "Analista de Recursos Humanos", "empresa": "Importante empresa del rubro retail",
        "ubicacion": "Lima",
        "sueldo_texto": "Sueldo a convenir",
        "html": """
        <p>Importante empresa requiere Analista de Recursos Humanos.</p>
        <p>Funciones:</p>
        <ul>
          <li>Apoyar en los procesos del área de recursos humanos</li>
          <li>Realizar el seguimiento de los indicadores del área</li>
          <li>Coordinar con las jefaturas los requerimientos de personal</li>
        </ul>
        <p>Requisitos:</p>
        <ul>
          <li>Experiencia en el puesto</li>
          <li>Disponibilidad inmediata</li>
          <li>Proactividad y trabajo en equipo</li>
        </ul>
        <p>Beneficios:</p>
        <ul>
          <li>Excelente ambiente laboral</li>
          <li>Oportunidad de crecimiento</li>
        </ul>""",
    },
    {   # tiene sueldo pero no dice qué se hace ni qué dan
        "fuente": "Bumeran", "dias": 4,
        "puesto": "Operario de Producción", "empresa": "Empresa líder",
        "ubicacion": "Lurín, Lima",
        "sueldo_texto": "S/ 1,300",
        "html": """
        <p>Se necesita operario de producción para planta en Lurín.
        Interesados enviar CV al correo indicado. Sueldo S/ 1,300.</p>
        <p>Requisitos: secundaria completa, disponibilidad inmediata,
        vivir en zonas aledañas.</p>""",
    },
    {   # aviso demasiado antiguo: publicado hace más de 2 meses
        "fuente": "Laborum", "dias": 75,
        "puesto": "Jefe de Tienda", "empresa": "Retail Perú SAC",
        "ubicacion": "Trujillo, La Libertad",
        "sueldo_texto": "S/ 4,200",
        "html": """
        <p>Funciones:</p>
        <ul>
          <li>Liderar el equipo de la tienda y cumplir la cuota mensual</li>
          <li>Controlar el inventario y las mermas del local</li>
          <li>Asegurar los estándares de atención al cliente</li>
        </ul>
        <p>Requisitos:</p>
        <ul>
          <li>3 años de experiencia como jefe o supervisor de tienda</li>
          <li>Titulado en Administración o afines</li>
          <li>Excel intermedio</li>
        </ul>
        <p>Beneficios:</p>
        <ul>
          <li>Planilla con beneficios de ley</li>
          <li>Bono por cumplimiento de metas</li>
          <li>Descuento de colaborador</li>
        </ul>""",
    },
]


class FuenteDemo(Fuente):
    """Reproduce el comportamiento de un portal, sin red."""

    nombre = "Demo"
    pausa = 0.0

    def recolectar(self, limite: int = 100) -> Iterator[OfertaCruda]:
        for aviso in AVISOS[:limite]:
            yield OfertaCruda(
                fuente=aviso["fuente"],
                url=f"https://ejemplo.pe/aviso/{abs(hash(aviso['puesto'])) % 10**6}",
                puesto=aviso["puesto"],
                empresa=aviso["empresa"],
                descripcion_html=aviso["html"],
                ubicacion_texto=aviso["ubicacion"],
                sueldo_texto=aviso["sueldo_texto"],
                publicado=_hace(aviso["dias"]),
            )
