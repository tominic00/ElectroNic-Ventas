import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import requests
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Electronic Ventas", layout="wide", initial_sidebar_state="expanded")

# --- CONEXIÓN A SUPABASE ---
SUPABASE_URL = "https://orligvvuajntokqxtajy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ybGlndnZ1YWpudG9rcXh0YWp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE4OTg3MTksImV4cCI6MjA5NzQ3NDcxOX0.9zewrwO1nrXIbp-Nx-x5hL1qVA28ZQDO7I2UgzjwQiA"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error al inicializar cliente Supabase: {e}")

if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

es_admin = st.session_state.admin_auth

# ==============================================================================
# FUNCIONES AUXILIARES Y FORMATOS
# ==============================================================================
def formato_dolares(valor):
    try:
        monto = f"{float(valor):,.2f}"
        return "U$S " + monto.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "U$S 0,00"

def formato_telefono(tel):
    t = "".join(filter(str.isdigit, str(tel)))
    if len(t) == 13 and t.startswith("549"): return f"+54 9 {t[3:6]}-{t[6:9]}-{t[9:]}"
    elif len(t) == 12 and t.startswith("54"): return f"+54 {t[2:5]}-{t[5:8]}-{t[8:]}"
    elif len(t) == 10: return f"+54 9 {t[0:3]}-{t[3:6]}-{t[6:]}"
    elif len(t) > 0: return f"+{t}"
    return "-"

@st.cache_data(ttl=300)
def obtener_dolar_blue():
    try:
        r = requests.get("https://dolarapi.com/v1/dolares/blue", timeout=5)
        return r.json()["compra"], r.json()["venta"]
    except:
        return 1000.0, 1000.0 

dolar_compra, dolar_venta = obtener_dolar_blue()

# --- MOTOR PDF PROFESIONAL CON PRECIOS UNITARIOS ---
def generar_presupuesto_pdf(cliente, lista_equipos, descuento, canje_info, valor_canje, total):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Encabezado Corporativo
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, 800, "ELECTRONIC")
    c.setFont("Helvetica", 10)
    c.drawString(50, 785, "Venta de iPhones Nuevos y Usados | Tucumán")
    
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(550, 800, "PRESUPUESTO OFICIAL")
    c.setFont("Helvetica", 10)
    c.drawRightString(550, 785, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}")
    
    c.setLineWidth(1)
    c.line(50, 770, 550, 770)
    
    # Datos del Cliente
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 745, "DATOS DEL CLIENTE:")
    c.setFont("Helvetica", 11)
    c.drawString(50, 725, f"Señor/a: {cliente}")
    
    c.line(50, 710, 550, 710)
    
    # Tabla de Productos
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 685, "DETALLE DEL PEDIDO:")
    
    # Encabezados de Tabla
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, 660, "Item / Descripción del Equipo")
    c.drawRightString(540, 660, "Precio Unitario")
    c.line(50, 650, 550, 650)
    
    c.setFont("Helvetica", 10)
    y = 630
    subtotal = 0.0
    for eq in lista_equipos:
        color_texto = f" - {eq.get('color', '')}" if eq.get('color') else ""
        c.drawString(60, y, f"• {eq['modelo']}{color_texto} (S/N: {eq['imei']})")
        c.drawRightString(540, y, formato_dolares(eq['precio_minorista']))
        subtotal += float(eq['precio_minorista'])
        y -= 22
        if y < 350: break 
        
    y -= 10
    c.line(50, y, 550, y)
    
    # Bloque de Totales y Ajustes
    y -= 25
    c.setFont("Helvetica", 11)
    c.drawString(320, y, "Subtotal Neto:")
    c.drawRightString(540, y, formato_dolares(subtotal))
    
    if descuento > 0:
        y -= 20
        c.drawString(320, y, "Descuentos Aplicados:")
        c.drawRightString(540, y, f"- {formato_dolares(descuento)}")
        
    if valor_canje > 0:
        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(320, y, "Plan Canje Recibido:")
        c.setFont("Helvetica", 10)
        c.drawString(60, y, f"🔄 Tomado en pago: {canje_info}")
        c.drawRightString(540, y, f"- {formato_dolares(valor_canje)}")
        
    y -= 15
    c.line(320, y, 540, y)
    
    y -= 25
    c.setFont("Helvetica-Bold", 14)
    c.drawString(320, y, "TOTAL COMPRA:")
    c.drawRightString(540, y, formato_dolares(total))
    
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 80, "* Cotización de referencia y stock garantizados por un periodo máximo de 24 horas.")
    c.drawString(50, 65, "* Los equipos tomados en Plan Canje se encuentran sujetos a verificación física final en el mostrador.")
    
    c.save()
    buffer.seek(0)
    return buffer

def traer_clientes():
    res = supabase.table("clientes_ventas").select("*").execute()
    return res.data if res.data else []


# ==============================================================================
# BARRA LATERAL
# ==============================================================================
with st.sidebar:
    st.title("Electronic Ventas")
    st.markdown("---")
    if not es_admin:
        st.subheader("🔒 Acceso Dueño")
        clave = st.text_input("Contraseña", type="password")
        if st.button("Desbloquear Sistema"):
            if clave == "admin123":
                st.session_state.admin_auth = True
                st.rerun()
            else: st.error("Clave incorrecta")
    else:
        st.success("🔓 MODO ADMINISTRADOR")
        if st.button("Cerrar Sesión (Bloquear)"):
            st.session_state.admin_auth = False
            st.rerun()

    st.markdown("---")
    st.subheader("💵 Cotización DolarHoy")
    st.metric("Compra", f"$ {dolar_compra:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("Venta", f"$ {dolar_venta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.markdown("---")
    st.subheader("🧮 Calculadora de Cobro")
    monto_pesos = st.number_input("Monto en ARS", min_value=0.0, step=1000.0)
    tasa_usar = dolar_compra if st.radio("Usar:", ["Compra", "Venta"]) == "Compra" else dolar_venta
    if monto_pesos > 0:
        st.success(f"Equivale a:\n### {formato_dolares(monto_pesos / tasa_usar)}")

# ==============================================================================
# PANTALLA PRINCIPAL
# ==============================================================================
st.title("🍏 Electronic — ERP de Ventas e Importación")
st.markdown("---")

tab_stock, tab_venta, tab_historial, tab_finanzas, tab_clientes, tab_directorio = st.tabs([
    "📦 Inventario", "🤝 Operaciones (Venta/Reserva)", "📋 Historial", "💰 Finanzas", "👤 Clientes y Deudas", "👥 Directorio"
])

# ----------------------------------------------------
# 1. INVENTARIO (CON FILTROS SEGREGADOS POR MODELO)
# ----------------------------------------------------
with tab_stock:
    st.header("Ingreso y Control de Stock")
    
    if es_admin:
        col1, col2, col3 = st.columns(3)
        with col1:
            mod_modelo = st.text_input("Modelo", placeholder="Ej: iPhone 15 Pro Max 256GB")
            mod_color = st.text_input("Color", placeholder="Ej: Titanium Blue, Blanco, etc.")
            mod_imei = st.text_input("IMEI")
            mod_condicion = st.selectbox("Condición", ["Sellado", "Usado", "CPO"])
            mod_bateria = "100%" if mod_condicion == "Sellado" else st.text_input("Batería %", value="100%")
        with col2:
            cst_equipo = st.number_input("Costo Equipo (U$S)", min_value=0.0, step=10.0)
            cst_carga = st.number_input("Carga (EEUU-TUC)", min_value=0.0, step=5.0)
            cst_finan = st.number_input("Intereses", min_value=0.0, step=5.0)
        with col3:
            pr_super = st.number_input("Precio Super Mayo (U$S)", min_value=0.0, step=10.0)
            pr_mayo = st.number_input("Precio Mayorista", min_value=0.0, step=10.0)
            pr_mino = st.number_input("Precio Minorista", min_value=0.0, step=10.0)

        if st.button("📥 GUARDAR EN INVENTARIO", type="primary", use_container_width=True):
            if mod_modelo and mod_imei:
                nuevo = {
                    "modelo": mod_modelo, "color": mod_color, "imei": mod_imei, "condicion": mod_condicion, "bateria": mod_bateria,
                    "costo_equipo": cst_equipo, "costo_importacion": cst_carga, "costo_financiero": cst_finan,
                    "precio_super_mayorista": pr_super, "precio_mayorista": pr_mayo, "precio_minorista": pr_mino,
                    "estado": "Disponible", "origen": "Importado"
                }
                supabase.table("inventario").insert(nuevo).execute()
                st.success("✅ Mercadería cargada correctamente.")
                st.rerun()
        st.markdown("---")

    # --- FILTROS SEGREGADOS POR MODELO ---
    st.subheader("🔍 Filtro Avanzado de Stock")
    res_stock = supabase.table("inventario").select("*").in_("estado", ["Disponible", "Reservado"]).execute()
    
    if res_stock.data:
        df_stock = pd.DataFrame(res_stock.data)
        
        # Selectbox dinámico para segregar modelos
        modelos_disponibles = sorted(df_stock["modelo"].unique().tolist())
        modelo_seleccionado = st.selectbox("🔲 Selecciona un modelo de iPhone para auditar stock presente:", ["Mostrar Todo"] + modelos_disponibles)
        
        df_filtrado = df_stock if modelo_seleccionado == "Mostrar Todo" else df_stock[df_stock["modelo"] == modelo_seleccionado]
        
        cant_disp = len(df_filtrado[df_filtrado["estado"] == "Disponible"])
        cant_res = len(df_filtrado[df_filtrado["estado"] == "Reservado"])
        
        st.info(f"📊 **Auditoría de {modelo_seleccionado}:** Disponibles en mostrador: **{cant_disp} unidades** | Reservados por pedido: **{cant_res} unidades**")
        
        if es_admin:
            st.dataframe(df_filtrado[["id", "modelo", "color", "condicion", "bateria", "imei", "origen", "estado", "costo_total", "precio_minorista"]], use_container_width=True, hide_index=True)
            
            st.markdown("### ✏️ Edición Completa de Parámetros de Stock")
            id_editar = st.selectbox("Seleccioná el ID del equipo a modificar:", df_filtrado["id"].tolist())
            if id_editar:
                eq_ed = df_filtrado[df_filtrado["id"] == id_editar].iloc[0]
                c_ed1, c_ed2, c_ed3 = st.columns(3)
                with c_ed1:
                    upd_mod = st.text_input("Modelo", value=eq_ed["modelo"], key="ue_m")
                    upd_color = st.text_input("Color", value=eq_ed.get("color", ""), key="ue_col")
                    upd_imei = st.text_input("IMEI", value=eq_ed["imei"], key="ue_i")
                    upd_cond = st.selectbox("Condición", ["Sellado", "Usado", "CPO"], index=["Sellado", "Usado", "CPO"].index(eq_ed["condicion"]) if eq_ed["condicion"] in ["Sellado", "Usado", "CPO"] else 0)
                    upd_bat = "100%" if upd_cond == "Sellado" else st.text_input("Batería %", value=eq_ed.get("bateria", "100%"))
                    upd_est = st.selectbox("Estado Stock", ["Disponible", "Reservado", "Vendido"], index=["Disponible", "Reservado", "Vendido"].index(eq_ed["estado"]))
                with c_ed2:
                    upd_cst_eq = st.number_input("Costo Equipo", value=float(eq_ed["costo_equipo"]))
                    upd_cst_cg = st.number_input("Carga EEUU-TUC", value=float(eq_ed["costo_importacion"]))
                    upd_cst_fi = st.number_input("Costo Financiero", value=float(eq_ed["costo_financiero"]))
                with c_ed3:
                    upd_prs = st.number_input("Precio Super Mayo (Base)", value=float(eq_ed["precio_super_mayorista"]))
                    upd_prmayo = st.number_input("Precio Mayorista", value=float(eq_ed["precio_mayorista"]))
                    upd_prmino = st.number_input("Precio Minorista (Público)", value=float(eq_ed["precio_minorista"]))
                    
                    if st.button("💾 Guardar Cambios Estructurales", type="primary", use_container_width=True):
                        supabase.table("inventario").update({
                            "modelo": upd_mod, "color": upd_color, "imei": upd_imei, "condicion": upd_cond, "bateria": upd_bat, "estado": upd_est,
                            "costo_equipo": upd_cst_eq, "costo_importacion": upd_cst_cg, "costo_financiero": upd_cst_fi,
                            "precio_super_mayorista": upd_prs, "precio_mayorista": upd_prmayo, "precio_minorista": upd_prmino
                        }).eq("id", int(id_editar)).execute()
                        st.success("Inventario sincronizado.")
                        st.rerun()
        else:
            df_vendedor = df_filtrado[["modelo", "color", "condicion", "bateria", "imei", "estado", "precio_minorista"]].copy()
            df_vendedor["precio_minorista"] = df_vendedor["precio_minorista"].apply(formato_dolares)
            df_vendedor.columns = ["Modelo", "Color", "Condición", "Batería", "IMEI", "Estado", "Precio Público (U$S)"]
            st.dataframe(df_vendedor, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay stock registrado en este momento.")

# ----------------------------------------------------
# 2. OPERACIONES: VENTAS, RESERVAS Y ANALYTICS VENDEDOR
# ----------------------------------------------------
with tab_venta:
    st.header("🤝 Gestión de Operaciones en Mostrador")
    
    v_op1, v_op2 = st.tabs(["🛒 Nueva Venta / Reserva", "📊 Rendimiento de Vendedores"])
    
    with v_op1:
        # LLAMADAS A LA BASE DE DATOS CORREGIDAS
        equipos_disp = supabase.table("inventario").select("*").eq("estado", "Disponible").execute().data or []
        clientes_list = traer_clientes()
        vendedores_list = supabase.table("vendedores").select("*").execute().data or []
        
        if not equipos_disp: 
            st.warning("No hay equipos en stock para operar.")
        else:
            st.subheader("1. Selección de Equipos en Lote")
            opciones_eq = {f"{e['modelo']} {e.get('color', '')} ({e.get('bateria','100%')}) - IMEI: {e['imei']} | {formato_dolares(e['precio_minorista'])}": e for e in equipos_disp}
            seleccionados_keys = st.multiselect("Selecciona los iPhones de la operación:", list(opciones_eq.keys()))
            
            if seleccionados_keys:
                equipos_seleccionados = [opciones_eq[k] for k in seleccionados_keys]
                subtotal_minorista = sum(float(e["precio_minorista"]) for e in equipos_seleccionados)
                subtotal_supermayo = sum(float(e["precio_super_mayorista"]) for e in equipos_seleccionados)
                costo_total_lote = sum(float(e["costo_total"]) for e in equipos_seleccionados)
                
                c_op1, c_op2 = st.columns(2)
                with c_op1:
                    st.subheader("2. Cliente y Asignación")
                    tipo_cli = st.radio("Cliente de la operación:", ["Existente", "Nuevo"], horizontal=True, key="tc_op")
                    if tipo_cli == "Existente" and clientes_list:
                        cliente_final = st.selectbox("Seleccionar Cliente:", [c["nombre"] for c in clientes_list], key="sc_op")
                    else:
                        cliente_final = st.text_input("Nombre del Cliente:", key="nc_op")
                        tel_cli = st.text_input("WhatsApp:", key="wc_op")
                        tipo_categoria = st.selectbox("Categoría:", ["Minorista", "Mayorista"], key="cc_op")
                    sel_vendedor = st.selectbox("Vendedor que atiende:", [v["nombre"] for v in vendedores_list], key="sv_op")
                    
                    st.subheader("3. Parámetros de Descuento")
                    descuento_manual = st.number_input("Descuento Manual Especial (U$S)", min_value=0.0, step=10.0)
                    descuento_lote = len(equipos_seleccionados) * 5.0 if len(equipos_seleccionados) >= 10 else 0.0
                    if descuento_lote > 0:
                        st.success(f"🔥 Descuento por lote automático activo: -{formato_dolares(descuento_lote)}")
                    descuento_total = descuento_manual + descuento_lote

                with c_op2:
                    st.subheader("4. Plan Canje (Usado)")
                    hay_canje = st.toggle("El cliente entrega un celular como pago", key="hc_op")
                    canje_mod = canje_bat = canje_imei = canje_color = ""
                    valor_canje = 0.0
                    if hay_canje:
                        with st.container(border=True):
                            canje_mod = st.text_input("Modelo del iPhone Usado", placeholder="Ej: iPhone 13 Pro Max")
                            canje_color = st.text_input("Color del Usado", placeholder="Ej: Space Gray")
                            cc_b, cc_i = st.columns(2)
                            canje_bat = cc_b.text_input("Batería Usado %")
                            canje_imei = cc_i.text_input("IMEI Usado")
                            valor_canje = st.number_input("Valor de Cotización Acordado (U$S)", min_value=0.0, step=10.0)

                total_operacion = subtotal_minorista - descuento_total - valor_canje
                st.markdown("---")
                st.subheader("5. Cierre de Caja")
                st.metric("TOTAL NETO A PAGAR POR EL CLIENTE", formato_dolares(total_operacion))
                
                monto_abonado = st.number_input("Monto que entrega en efectivo hoy (U$S)", min_value=0.0, max_value=float(total_operacion), value=float(total_operacion), step=10.0)
                
                comision_calculada = (subtotal_minorista - descuento_total) - subtotal_supermayo
                ganancia_local = subtotal_supermayo - costo_total_lote
                
                b_acc1, b_acc2, b_acc3 = st.columns(3)
                
                with b_acc1:
                    if st.button("📄 GENERAR PRESUPUESTO DETALLADO (PDF)", use_container_width=True):
                        info_canje_pdf = f"{canje_mod} {canje_color} ({canje_bat}%)" if hay_canje else ""
                        pdf = generar_presupuesto_pdf(cliente_final, equipos_seleccionados, descuento_total, info_canje_pdf, valor_canje, total_operacion)
                        st.download_button("Descargar PDF Comercial", pdf, f"Presupuesto_{cliente_final}.pdf", "application/pdf", use_container_width=True)
                        
                with b_acc2:
                    if st.button("📦 GENERAR PEDIDO (RESERVAR STOCK)", use_container_width=True):
                        if cliente_final and sel_vendedor:
                            if tipo_cli == "Nuevo":
                                supabase.table("clientes_ventas").insert({"nombre": cliente_final, "contacto": tel_cli, "tipo": tipo_categoria}).execute()
                            
                            ids_lote = [int(e['id']) for e in equipos_seleccionados]
                            nombres_lote = ", ".join([f"{e['modelo']} {e.get('color', '')}" for e in equipos_seleccionados])
                            
                            for eq_id in ids_lote:
                                supabase.table("inventario").update({"estado": "Reservado"}).eq("id", eq_id).execute()
                            
                            supabase.table("pedidos").insert({
                                "cliente_nombre": cliente_final, "vendedor_nombre": sel_vendedor,
                                "equipos_reservados": nombres_lote, "ids_equipos": ids_lote, "total_pedido": total_operacion
                            }).execute()
                            st.success(f"🎉 Pedido Registrado. Stock congelado para {cliente_final}.")
                            st.rerun()
                        else: st.error("Faltan campos obligatorios.")

                with b_acc3:
                    if st.button("🚀 CONFIRMAR VENTA INMEDIATA", type="primary", use_container_width=True):
                        if cliente_final and sel_vendedor:
                            if tipo_cli == "Nuevo":
                                supabase.table("clientes_ventas").insert({"nombre": cliente_final, "contacto": tel_cli, "tipo": tipo_categoria}).execute()

                            for eq in equipos_seleccionados:
                                supabase.table("inventario").update({"estado": "Vendido"}).eq("id", eq['id']).execute()
                            
                            if hay_canje and canje_mod:
                                eq_canje = {
                                    "modelo": canje_mod, "color": canje_color, "imei": canje_imei, "condicion": "Usado", "bateria": canje_bat,
                                    "costo_equipo": valor_canje, "costo_importacion": 0, "costo_financiero": 0,
                                    "precio_super_mayorista": valor_canje + 50, "precio_mayorista": valor_canje + 100, "precio_minorista": valor_canje + 150,
                                    "estado": "Disponible", "origen": "Canje"
                                }
                                supabase.table("inventario").insert(eq_canje).execute()

                            hist_p = [{"fecha": str(datetime.date.today()), "monto": float(monto_abonado)}] if monto_abonado > 0 else []
                            
                            str_vendido = ", ".join([f"{e['modelo']} {e.get('color', '')}" for e in equipos_seleccionados])
                            
                            supabase.table("ventas").insert({
                                "cliente_nombre": cliente_final, "vendedor_nombre": sel_vendedor,
                                "equipo_vendido": str_vendido,
                                "precio_final_venta": subtotal_minorista - descuento_total, "descuento_aplicado": descuento_total,
                                "equipo_recibido_canje": f"{canje_mod} {canje_color}" if hay_canje else "Ninguno", 
                                "canje_imei": canje_imei, "canje_bateria": canje_bat, "cotizacion_canje": valor_canje,
                                "monto_abonado": monto_abonado, "historial_pagos": hist_p, "comision_vendedor": comision_calculada, "ganancia_neta_local": ganancia_local, "comision_pagada": False
                            }).execute()
                            st.success("🎉 ¡Venta y caja cerradas con éxito!")
                            st.rerun()
                        else: st.error("Faltan campos obligatorios.")

    with v_op2:
        st.subheader("📊 Producción de Vendedores")
        c_fe1, c_fe2 = st.columns(2)
        f_v_desde = c_fe1.date_input("Filtrar desde:", datetime.date.today().replace(day=1), key="fvd")
        f_v_hasta = c_fe2.date_input("Filtrar hasta:", datetime.date.today(), key="fvh")
        
        res_v_perf = supabase.table("ventas").select("*").gte("fecha_venta", str(f_v_desde)).lte("fecha_venta", str(f_v_hasta)).execute()
        if res_v_perf.data:
            df_perf = pd.DataFrame(res_v_perf.data)
            perf_resumen = df_perf.groupby("vendedor_nombre").agg({"precio_final_venta":"sum", "comision_vendedor":"sum", "id":"count"}).reset_index()
            perf_resumen.columns = ["Vendedor", "Total Facturado (U$S)", "Comisiones Generadas (U$S)", "Equipos Vendidos"]
            
            perf_resumen["Total Facturado (U$S)"] = perf_resumen["Total Facturado (U$S)"].apply(formato_dolares)
            perf_resumen["Comisiones Generadas (U$S)"] = perf_resumen["Comisiones Generadas (U$S)"].apply(formato_dolares)
            
            st.dataframe(perf_resumen, hide_index=True, use_container_width=True)
        else: st.info("No se registran operaciones en el rango de fechas seleccionado.")

# ----------------------------------------------------
# 3. HISTORIAL (INCLUYE GESTIÓN DE PEDIDOS PENDIENTES)
# ----------------------------------------------------
with tab_historial:
    st.header("📋 Monitoreo de Operaciones")
    
    h_v1, h_v2 = st.tabs(["Ventas Confirmadas", "Pedidos y Reservas Activas"])
    
    with h_v1:
        res_v = supabase.table("ventas").select("*").order("id", desc=True).execute()
        if res_v.data:
            df_v = pd.DataFrame(res_v.data)
            df_v_show = df_v[["fecha_venta", "equipo_vendido", "precio_final_venta", "equipo_recibido_canje", "monto_abonado", "cliente_nombre", "vendedor_nombre"]].copy()
            df_v_show["precio_final_venta"] = df_v_show["precio_final_venta"].apply(formato_dolares)
            df_v_show["monto_abonado"] = df_v_show["monto_abonado"].apply(formato_dolares)
            st.dataframe(df_v_show, use_container_width=True, hide_index=True)
        else: st.info("Sin registros.")
        
    with h_v2:
        res_pedidos = supabase.table("pedidos").select("*").eq("estado", "Pendiente").execute()
        if res_pedidos.data:
            df_p = pd.DataFrame(res_pedidos.data)
            st.dataframe(df_p[["id", "fecha_pedido", "cliente_nombre", "equipos_reservados", "total_pedido", "vendedor_nombre"]], use_container_width=True, hide_index=True)
            
            id_p_entregar = st.selectbox("Seleccionar ID de Pedido para facturar y entregar:", df_p["id"].tolist())
            if st.button("🚀 Facturar y Entregar Pedido", type="primary"):
                p_obj = df_p[df_p["id"] == id_p_entregar].iloc[0]
                
                for eq_id in p_obj["ids_equipos"]:
                    supabase.table("inventario").update({"estado": "Vendido"}).eq("id", int(eq_id)).execute()
                    
                supabase.table("pedidos").update({"estado": "Completado"}).eq("id", int(id_p_entregar)).execute()
                
                supabase.table("ventas").insert({
                    "cliente_nombre": p_obj["cliente_nombre"], "vendedor_nombre": p_obj["vendedor_nombre"],
                    "equipo_vendido": p_obj["equipos_reservados"], "precio_final_venta": p_obj["total_pedido"],
                    "monto_abonado": p_obj["total_pedido"], "ganancia_neta_local": 0, "comision_vendedor": 0
                }).execute()
                st.success("¡Pedido entregado y facturado!")
                st.rerun()
        else: st.success("No hay reservas ni pedidos pendientes reteniendo stock.")

# ----------------------------------------------------
# 4. FINANZAS
# ----------------------------------------------------
with tab_finanzas:
    if es_admin:
        st.header("💰 Finanzas, Caja y Liquidaciones")
        f_inicio, f_fin = st.columns(2)
        fecha_desde = f_inicio.date_input("Desde:", datetime.date.today().replace(day=1), key="fd_fin")
        fecha_hasta = f_fin.date_input("Hasta:", datetime.date.today(), key="fh_fin")
        
        res_f = supabase.table("ventas").select("*").gte("fecha_venta", str(fecha_desde)).lte("fecha_venta", str(fecha_hasta)).execute()
        if res_f.data:
            df_f = pd.DataFrame(res_f.data)
            df_f["comision_pagada"] = df_f["comision_pagada"].fillna(False)
            st.metric("Ganancia Neta Pura del Local (en este período)", formato_dolares(df_f["ganancia_neta_local"].sum()))
            
            st.markdown("---")
            st.subheader("🧑‍💼 Comisiones Pendientes")
            df_pendientes = df_f[df_f["comision_pagada"] == False]
            if not df_pendientes.empty:
                liq = df_pendientes.groupby("vendedor_nombre")["comision_vendedor"].sum().reset_index()
                liq.columns = ["Vendedor", "Comisión Pendiente a Pagar"]
                
                col_liq1, col_liq2 = st.columns(2)
                with col_liq1:
                    st.dataframe(liq.style.format({"Comisión Pendiente a Pagar": "${:,.2f}"}), hide_index=True, use_container_width=True)
                with col_liq2:
                    vend_a_pagar = st.selectbox("Seleccionar Vendedor a Liquidar:", liq["Vendedor"].tolist())
                    if st.button("Marcar Comisiones como Pagadas", type="primary"):
                        ids_a_pagar = df_pendientes[df_pendientes["vendedor_nombre"] == vend_a_pagar]["id"].tolist()
                        for id_v in ids_a_pagar:
                            supabase.table("ventas").update({"comision_pagada": True, "fecha_pago_comision": str(datetime.date.today())}).eq("id", id_v).execute()
                        st.success(f"¡Comisiones de {vend_a_pagar} liquidadas correctamente!")
                        st.rerun()
            else: st.success("Todas las comisiones están pagadas.")
            
            st.markdown("---")
            st.subheader("📚 Historial de Comisiones Pagadas")
            df_pagadas = df_f[df_f["comision_pagada"] == True]
            if not df_pagadas.empty:
                df_hist_comis = df_pagadas[["fecha_pago_comision", "vendedor_nombre", "equipo_vendido", "comision_vendedor"]].copy()
                df_hist_comis["comision_vendedor"] = df_hist_comis["comision_vendedor"].apply(formato_dolares)
                df_hist_comis.columns = ["Fecha de Pago", "Vendedor", "Venta", "Monto"]
                st.dataframe(df_hist_comis, hide_index=True, use_container_width=True)
        else: st.info("Sin registros en este rango de fechas.")
    else: st.error("🔒 El área de finanzas es privada del Administrador.")

# ----------------------------------------------------
# 5. CLIENTES Y DEUDAS
# ----------------------------------------------------
with tab_clientes:
    st.header("👤 Directorio de Clientes y Cobranzas")
    clientes_list = traer_clientes()
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.subheader("✏️ Modificar Ficha de Cliente")
        if clientes_list:
            dic_cli = {c["nombre"]: c for c in clientes_list}
            sel_cli_ed = st.selectbox("Seleccionar Cliente a modificar:", list(dic_cli.keys()))
            cli_data = dic_cli[sel_cli_ed]
            
            upd_cli_nom = st.text_input("Nombre / Razón Social", value=cli_data["nombre"])
            upd_cli_tel = st.text_input("WhatsApp de Contacto", value=cli_data.get("contacto", ""))
            upd_cli_tipo = st.selectbox("Categoría Comercial", ["Minorista", "Mayorista"], index=["Minorista", "Mayorista"].index(cli_data.get("tipo", "Minorista")) if cli_data.get("tipo") in ["Minorista", "Mayorista"] else 0)
            
            if st.button("Guardar Cambios de Cliente", use_container_width=True):
                supabase.table("clientes_ventas").update({"nombre": upd_cli_nom, "contacto": upd_cli_tel, "tipo": upd_cli_tipo}).eq("id", cli_data["id"]).execute()
                if upd_cli_nom != cli_data["nombre"]:
                    supabase.table("ventas").update({"cliente_nombre": upd_cli_nom}).eq("cliente_nombre", cli_data["nombre"]).execute()
                st.success("Ficha actualizada.")
                st.rerun()
                
    with col_c2:
        st.subheader("💸 Cargar Entrega de Dinero / Cobro")
        res_vtas = supabase.table("ventas").select("*").execute()
        if res_vtas.data:
            df_v = pd.DataFrame(res_vtas.data)
            df_v["Deuda"] = df_v["precio_final_venta"] - df_v["monto_abonado"]
            df_deudoras = df_v[df_v["Deuda"] > 0]
            
            if not df_deudoras.empty:
                opciones_deuda = {f"Venta N° {v['id']} - {v['cliente_nombre']} (Debe: {formato_dolares(v['Deuda'])})": v for _, v in df_deudoras.iterrows()}
                sel_v_deuda = st.selectbox("Seleccionar cuenta a entregar dinero:", list(opciones_deuda.keys()))
                v_obj = opciones_deuda[sel_v_deuda]
                
                nuevo_cobro = st.number_input("Monto en Dólares entregado hoy (U$S)", min_value=0.0, max_value=float(v_obj["Deuda"]), step=10.0)
                if st.button("Registrar Cobro en Cuenta Corriente", type="primary", use_container_width=True):
                    historial_p = v_obj.get("historial_pagos") or []
                    historial_p.append({"fecha": str(datetime.date.today()), "monto": float(nuevo_cobro)})
                    supabase.table("ventas").update({"monto_abonado": float(v_obj["monto_abonado"]) + float(nuevo_cobro), "historial_pagos": historial_p}).eq("id", v_obj["id"]).execute()
                    st.success("Pago imputado correctamente.")
                    st.rerun()
            else: st.success("Cuentas corrientes al día.")

    st.markdown("---")
    st.write("### 📊 Estado General de Cuentas")
    if res_vtas.data:
        resumen_cli = df_v.groupby("cliente_nombre").agg({"precio_final_venta":"sum", "monto_abonado":"sum", "Deuda":"sum"}).reset_index()
        resumen_cli.columns = ["Cliente", "Total Comprado", "Total Pagado", "Deuda Pendiente"]
        
        resumen_cli["Total Comprado"] = resumen_cli["Total Comprado"].apply(formato_dolares)
        resumen_cli["Total Pagado"] = resumen_cli["Total Pagado"].apply(formato_dolares)
        resumen_cli["Deuda Pendiente"] = resumen_cli["Deuda Pendiente"].apply(formato_dolares)
        st.dataframe(resumen_cli, hide_index=True, use_container_width=True)

# ----------------------------------------------------
# 6. DIRECTORIO
# ----------------------------------------------------
with tab_directorio:
    if es_admin:
        st.header("👥 Gestión de Personal Vendedor")
        nuevo_vend = st.text_input("Ingresar nombre completo del comisionista:")
        if st.button("Dar de Alta Vendedor", type="primary"):
            if nuevo_vend:
                supabase.table("vendedores").insert({"nombre": nuevo_vend}).execute()
                st.success("Alta registrada.")
                st.rerun()
        v_list = supabase.table("vendedores").select("*").execute().data
        if v_list:
            st.dataframe(pd.DataFrame(v_list)[["nombre"]], hide_index=True, use_container_width=True)
    else: st.error("🔒 Acceso privado de administración.")
