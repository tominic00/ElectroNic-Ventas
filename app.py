import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import requests
import io
import re
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

def generar_presupuesto_pdf(cliente, lista_equipos, descuento, canje_info, valor_canje, total, deuda_anterior=0.0):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
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
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 745, "DATOS DEL CLIENTE:")
    c.setFont("Helvetica", 11)
    c.drawString(50, 725, f"Señor/a: {cliente}")
    c.line(50, 710, 550, 710)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 685, "DETALLE DEL PEDIDO:")
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
    y -= 25
    c.setFont("Helvetica", 11)
    c.drawString(320, y, "Subtotal Neto Pedido:")
    c.drawRightString(540, y, formato_dolares(subtotal))
    if descuento > 0:
        y -= 20
        c.drawString(320, y, "Descuentos Aplicados:")
        c.drawRightString(540, y, f"- {formato_dolares(descuento)}")
    if valor_canje > 0:
        y -= 20
        c.drawString(320, y, "Plan Canje Recibido:")
        c.drawString(60, y, f"🔄 Tomado en pago: {canje_info}")
        c.drawRightString(540, y, f"- {formato_dolares(valor_canje)}")
    y -= 15
    c.line(320, y, 540, y)
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(320, y, "TOTAL ESTE PEDIDO:")
    c.drawRightString(540, y, formato_dolares(total))
    
    y -= 35
    c.line(50, y, 550, y)
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "📊 ESTADO DE CUENTA CORRIENTE ACUMULADA")
    y -= 22
    c.setFont("Helvetica", 11)
    c.drawString(60, y, f"Saldo Deuda Histórica Anterior:")
    c.drawRightString(540, y, formato_dolares(deuda_anterior))
    y -= 20
    c.drawString(60, y, f"+ Saldo de este nuevo pedido:")
    c.drawRightString(540, y, formato_dolares(total))
    y -= 10
    c.line(320, y, 540, y)
    y -= 25
    nueva_deuda_total = deuda_anterior + total
    c.setFont("Helvetica-Bold", 13)
    c.drawString(60, y, "🚀 NUEVA DEUDA TOTAL ACUMULADA:")
    c.drawRightString(540, y, formato_dolares(nueva_deuda_total))
    y -= 15
    c.line(50, y, 550, y)
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

# ==============================================================================
# PANTALLA PRINCIPAL
# ==============================================================================
st.title("🍏 Electronic — ERP de Ventas e Importación")
st.markdown("---")

tab_stock, tab_venta, tab_pedidos, tab_historial, tab_finanzas, tab_clientes, tab_directorio = st.tabs([
    "📦 Inventario", "🤝 Nueva Operación", "📋 Pedidos Activos", "📜 Historial Ventas", "💰 Finanzas", "👤 Clientes", "👥 Personal"
])

# ----------------------------------------------------
# 1. INVENTARIO
# ----------------------------------------------------
with tab_stock:
    res_all_stock = supabase.table("inventario").select("*").in_("estado", ["Disponible", "Reservado"]).execute()
    df_all = pd.DataFrame(res_all_stock.data) if res_all_stock.data else pd.DataFrame()
    
    if es_admin:
        with st.expander("📥 Cargar Stock (Ingreso Individual)"):
            col1, col2, col3 = st.columns(3)
            with col1:
                mod_modelo = st.text_input("Modelo", placeholder="Ej: iPhone 17 Pro Max 256GB")
                mod_color = st.text_input("Color", placeholder="Ej: Titanium Natural")
                mod_imei = st.text_input("IMEI")
                mod_condicion = st.selectbox("Condición", ["Sellado", "Usado", "CPO"])
                mod_bateria = "100%" if mod_condicion == "Sellado" else st.text_input("Batería %", value="100%")
            with col2:
                cst_equipo = st.number_input("Costo Equipo (U$S)", min_value=0.0)
                cst_carga = st.number_input("Carga (EEUU-TUC)", min_value=0.0)
                cst_finan = st.number_input("Intereses", min_value=0.0)
            with col3:
                pr_super = st.number_input("Precio Super Mayo (U$S)", min_value=0.0)
                pr_mayo = st.number_input("Precio Mayorista", min_value=0.0)
                pr_mino = st.number_input("Precio Minorista", min_value=0.0)

            if st.button("📥 GUARDAR EN STOCK", type="primary", use_container_width=True):
                if mod_modelo and mod_imei:
                    supabase.table("inventario").insert({
                        "modelo": str(mod_modelo), "color": str(mod_color), "imei": str(mod_imei), "condicion": str(mod_condicion), "bateria": str(mod_bateria),
                        "costo_equipo": float(cst_equipo), "costo_importacion": float(cst_carga), "costo_financiero": float(cst_finan),
                        "precio_super_mayorista": float(pr_super), "precio_mayorista": float(pr_mayo), "precio_minorista": float(pr_mino), "estado": "Disponible", "origen": "Importado"
                    }).execute()
                    st.success("✅ Guardado.")
                    st.rerun()

        if not df_all.empty:
            with st.expander("⚡ ACTUALIZACIÓN MASIVA DE PRECIOS Y COSTOS"):
                tipo_remarca = st.radio("Método de remarcación:", ["Por Modelo de Celular", "Por Selección Manual de Equipos"], horizontal=True)
                equipos_a_modificar_ids = []
                if tipo_remarca == "Por Modelo de Celular":
                    modelo_masivo = st.selectbox("Seleccioná el modelo exacto a remarcar:", sorted(df_all["modelo"].unique().tolist()))
                    equipos_a_modificar_ids = df_all[df_all["modelo"] == modelo_masivo]["id"].tolist()
                else:
                    df_all["info_selec"] = df_all["modelo"] + " [" + df_all["color"] + "] - IMEI: " + df_all["imei"]
                    dic_masivo = {row["info_selec"]: row["id"] for _, row in df_all.iterrows()}
                    selec_manuales = st.multiselect("Seleccioná los equipos:", list(dic_masivo.keys()))
                    equipos_a_modificar_ids = [dic_masivo[k] for k in selec_manuales]

                if equipos_a_modificar_ids:
                    rm_c1, rm_c2, rm_c3 = st.columns(3)
                    new_costo_eq = rm_c1.number_input("Nuevo Costo Equipo (U$S)", min_value=0.0)
                    new_costo_cg = rm_c1.number_input("Nuevo Costo Carga (U$S)", min_value=0.0)
                    new_p_super = rm_c2.number_input("Nuevo Precio Super Mayo (U$S)", min_value=0.0)
                    new_p_mayo = rm_c2.number_input("Nuevo Precio Mayorista (U$S)", min_value=0.0)
                    new_p_mino = rm_c3.number_input("Nuevo Precio Minorista (U$S)", min_value=0.0)
                    
                    if st.button("⚡ APLICAR CAMBIOS MASIVOS AHORA", type="primary", use_container_width=True):
                        upd_data = {}
                        if new_costo_eq > 0: upd_data["costo_equipo"] = float(new_costo_eq)
                        if new_costo_cg > 0: upd_data["costo_importacion"] = float(new_costo_cg)
                        if new_p_super > 0: upd_data["precio_super_mayorista"] = float(new_p_super)
                        if new_p_mayo > 0: upd_data["precio_mayorista"] = float(new_p_mayo)
                        if new_p_mino > 0: upd_data["precio_minorista"] = float(new_p_mino)
                        
                        if upd_data:
                            for eq_id in equipos_a_modificar_ids:
                                supabase.table("inventario").update(upd_data).eq("id", int(eq_id)).execute()
                            st.success("🎉 ¡Remarcación masiva completada!")
                            st.rerun()

    if not df_all.empty:
        st.subheader("🔍 Filtro y Visualización de Stock")
        mod_sel = st.selectbox("Filtrar vista por modelo:", ["Mostrar Todo"] + sorted(df_all["modelo"].unique().tolist()))
        df_v = df_all if mod_sel == "Mostrar Todo" else df_all[df_all["modelo"] == mod_sel]
        
        if es_admin:
            st.dataframe(df_v[["id", "modelo", "color", "condicion", "bateria", "imei", "estado", "costo_total", "precio_super_mayorista", "precio_minorista"]], use_container_width=True, hide_index=True)
            
            st.markdown("### ✏️ Panel de Gestión de Ficha (Editar / Eliminar)")
            id_ed = st.selectbox("Seleccionar ID del equipo en stock para gestionar:", df_v["id"].tolist())
            if id_ed:
                eq = df_v[df_v["id"] == id_ed].iloc[0]
                ed_c1, ed_c2 = st.columns(2)
                ed_mod = ed_c1.text_input("Modelo", value=eq["modelo"], key="ed_m")
                ed_col = ed_c1.text_input("Color", value=eq.get("color",""), key="ed_c")
                ed_imei = ed_c1.text_input("IMEI", value=eq["imei"], key="ed_i")
                ed_p_mino = ed_c2.number_input("Precio Público", value=float(eq["precio_minorista"]))
                ed_p_super = ed_c2.number_input("Precio Super Mayo", value=float(eq["precio_super_mayorista"]))
                
                b_ed1, b_ed2 = st.columns(2)
                with b_ed1:
                    if st.button("💾 Guardar Cambios Individuales", use_container_width=True):
                        supabase.table("inventario").update({
                            "modelo": str(ed_mod), "color": str(ed_col), "imei": str(ed_imei), 
                            "precio_minorista": float(ed_p_mino), "precio_super_mayorista": float(ed_p_super)
                        }).eq("id", int(id_ed)).execute()
                        st.success("Sincronizado.")
                        st.rerun()
                with b_ed2:
                    if st.button("🗑️ ELIMINAR CELULAR DEL STOCK PERMANENTEMENTE", type="primary", use_container_width=True):
                        supabase.table("inventario").delete().eq("id", int(id_ed)).execute()
                        st.success("Equipo eliminado de las bases de datos.")
                        st.rerun()
        else:
            df_vend = df_v[["modelo", "color", "condicion", "bateria", "precio_minorista"]].copy()
            df_vend["precio_minorista"] = df_vend["precio_minorista"].apply(formato_dolares)
            st.dataframe(df_vend, use_container_width=True, hide_index=True)
    else: st.warning("Sin stock disponible.")

# ----------------------------------------------------
# 2. OPERACIONES (VENTAS Y PEDIDOS)
# ----------------------------------------------------
with tab_venta:
    st.header("🤝 Cerrar Operación en Mostrador")
    
    equipos_disp = supabase.table("inventario").select("*").eq("estado", "Disponible").execute().data or []
    clientes_list = traer_clientes()
    vendedores_list = supabase.table("vendedores").select("*").execute().data or []
    
    if not equipos_disp: st.warning("No hay stock para operar.")
    else:
        opciones_eq = {f"{e['modelo']} {e.get('color','')} - S/N: {e['imei']} | {formato_dolares(e['precio_minorista'])}": e for e in equipos_disp}
        lote_keys = st.multiselect("Seleccioná los equipos de la operación:", list(opciones_eq.keys()))
        
        if lote_keys:
            eq_lote = [opciones_eq[k] for k in lote_keys]
            sub_mino = sum(float(e["precio_minorista"]) for e in eq_lote)
            sub_super = sum(float(e["precio_super_mayorista"]) for e in eq_lote)
            cst_lote = sum(float(e["costo_total"]) for e in eq_lote)
            
            st.info(f"📦 Lote: {len(eq_lote)} equipos | Subtotal: {formato_dolares(sub_mino)}")
            
            c1, c2 = st.columns(2)
            with c1:
                tipo_c = st.radio("Cliente:", ["Existente", "Nuevo"], horizontal=True)
                cliente_final = st.selectbox("Seleccionar:", [c["nombre"] for c in clientes_list]) if tipo_c == "Existente" and clientes_list else st.text_input("Nombre Cliente:")
                sel_vendedor = st.selectbox("Vendedor:", [v["nombre"] for v in vendedores_list]) if vendedores_list else "Dueño"
                desc_manual = st.number_input("Descuento Manual (U$S)", min_value=0.0)
                desc_lote = len(eq_lote) * 5.0 if len(eq_lote) >= 10 else 0.0
                desc_total = float(desc_manual + desc_lote)
            with c2:
                hay_canje = st.toggle("¿Hay Plan Canje?")
                canje_mod = canje_col = canje_bat = canje_imei = ""
                val_canje = 0.0
                if hay_canje:
                    canje_mod = st.text_input("Modelo Usado")
                    canje_col = st.text_input("Color Usado")
                    canje_bat = st.text_input("Batería %")
                    canje_imei = st.text_input("IMEI Usado")
                    val_canje = st.number_input("Cotización Usado (U$S)", min_value=0.0)

            total_op = float(sub_mino - desc_total - val_canje)
            st.markdown("---")
            st.subheader(f"Total Neto Operación: {formato_dolares(total_op)}")
            
            comision = float((sub_mino - desc_total) - sub_super)
            ganancia = float(sub_super - cst_lote)
            
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("📄 GENERAR PDF"):
                    pdf = generar_presupuesto_pdf(cliente_final, eq_lote, desc_total, f"{canje_mod} {canje_col}", val_canje, total_op)
                    st.download_button("Descargar Presupuesto", pdf, f"Presupuesto_{cliente_final}.pdf", "application/pdf")
            
            with b2:
                if st.button("📦 RESERVAR (CREAR PEDIDO)", type="secondary", use_container_width=True):
                    if cliente_final and sel_vendedor:
                        ids_lote = [int(e['id']) for e in eq_lote]
                        nombres_lote = ", ".join([f"{e['modelo']} {e.get('color','')} [IMEI: {e['imei']}]" for e in eq_lote])
                        
                        for eq_id in ids_lote:
                            supabase.table("inventario").update({"estado": "Reservado"}).eq("id", eq_id).execute()
                        
                        supabase.table("pedidos").insert({
                            "cliente_nombre": str(cliente_final), "vendedor_nombre": str(sel_vendedor),
                            "equipos_reservados": str(nombres_lote), "ids_equipos": ids_lote, 
                            "total_pedido": float(total_op), "comision_vendedor": float(comision), 
                            "ganancia_neta_local": float(ganancia), "estado": "Pendiente",
                            "equipo_recibido_canje": str(canje_mod) if hay_canje else "Ninguno",
                            "canje_color": str(canje_col) if hay_canje else "",
                            "canje_bateria": str(canje_bat) if hay_canje else "",
                            "canje_imei": str(canje_imei) if hay_canje else "",
                            "cotizacion_canje": float(val_canje) if hay_canje else 0.0
                        }).execute()
                        st.success("🎉 ¡Pedido registrado y datos de canje blindados en la reserva!")
                        st.rerun()

            with b3:
                if st.button("🚀 CERRAR VENTA DIRECTA", type="primary", use_container_width=True):
                    if cliente_final and sel_vendedor:
                        for e in eq_lote:
                            supabase.table("inventario").update({"estado": "Vendido"}).eq("id", int(e['id'])).execute()
                        if hay_canje and canje_mod:
                            supabase.table("inventario").insert({
                                "modelo": str(canje_mod), "color": str(canje_col), "imei": str(canje_imei), 
                                "condicion": "Usado", "bateria": str(canje_bat), "costo_equipo": float(val_canje), 
                                "precio_minorista": float(val_canje+150), "estado": "Disponible", "origen": "Canje"
                            }).execute()
                        
                        str_vendido = ", ".join([f"{e['modelo']} {e.get('color','')} [IMEI: {e['imei']}]" for e in eq_lote])
                        
                        supabase.table("ventas").insert({
                            "cliente_nombre": str(cliente_final), "vendedor_nombre": str(sel_vendedor), 
                            "equipo_vendido": str(str_vendido),
                            "precio_final_venta": float(sub_mino - desc_total), "descuento_aplicado": float(desc_total), 
                            "equipo_recibido_canje": str(canje_mod) if hay_canje else "Ninguno", "cotizacion_canje": float(val_canje), 
                            "monto_abonado": float(total_op), "comision_vendedor": float(comision), 
                            "ganancia_neta_local": float(ganancia), "comision_pagada": False,
                            "historial_pagos": [{"fecha": str(datetime.date.today()), "monto": float(total_op)}] if total_op > 0 else []
                        }).execute()
                        st.success("🎉 Venta confirmada.")
                        st.rerun()

# ----------------------------------------------------
# 3. GESTIÓN DE PEDIDOS ACTIVOS
# ----------------------------------------------------
with tab_pedidos:
    st.header("📋 Panel de Pedidos y Reservas Pendientes")
    
    res_p_activos = supabase.table("pedidos").select("*").eq("estado", "Pendiente").order("id", desc=True).execute()
    if res_p_activos.data:
        df_p = pd.DataFrame(res_p_activos.data)
        
        df_p_show = df_p[["id", "fecha_pedido", "cliente_nombre", "equipos_reservados", "total_pedido", "vendedor_nombre"]].copy()
        df_p_show["total_pedido"] = df_p_show["total_pedido"].apply(formato_dolares)
        df_p_show.columns = ["N° Pedido", "Fecha Reserva", "Cliente", "iPhones Reservados y Lista de IMEIs", "Total Efectivo a Cobrar", "Vendedor"]
        st.dataframe(df_p_show, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("⚡ Acciones del Pedido Seleccionado")
        id_p_facturar = st.selectbox("Seleccioná el N° de Pedido:", df_p["id"].tolist())
        
        if id_p_facturar:
            p_sel = df_p[df_p["id"] == id_p_facturar].iloc[0]
            
            res_v_cli = supabase.table("ventas").select("precio_final_venta", "monto_abonado").eq("cliente_nombre", p_sel["cliente_nombre"]).execute()
            deuda_anterior = 0.0
            if res_v_cli.data:
                for v in res_v_cli.data:
                    deuda_anterior += max(0.0, float(v["precio_final_venta"]) - float(v["monto_abonado"]))
            
            col_bp1, col_b2, col_b3 = st.columns(3)
            
            with col_bp1:
                lista_equipos_pdf = []
                if "ids_equipos" in p_sel and p_sel["ids_equipos"]:
                    res_eq_p = supabase.table("inventario").select("*").in_("id", p_sel["ids_equipos"]).execute()
                    if res_eq_p.data: lista_equipos_pdf = res_eq_p.data
                
                canje_txt = f"{p_sel.get('equipo_recibido_canje','')} {p_sel.get('canje_color','')}" if p_sel.get('equipo_recibido_canje') != 'Ninguno' else 'Ninguno'
                pdf_pedido = generar_presupuesto_pdf(p_sel["cliente_nombre"], lista_equipos_pdf, 0.0, canje_txt, float(p_sel.get("cotizacion_canje", 0.0)), float(p_sel["total_pedido"]), deuda_anterior)
                st.download_button("📄 EMITIR PDF CON DEUDA", pdf_pedido, f"Pedido_{id_p_facturar}.pdf", "application/pdf", use_container_width=True)
            
            with col_b2:
                if st.button("🚀 CONFIRMAR ENTREGA Y FACTURAR VENTA", type="primary", use_container_width=True):
                    for eq_id in p_sel["ids_equipos"]:
                        supabase.table("inventario").update({"estado": "Vendido"}).eq("id", int(eq_id)).execute()
                    
                    c_mod = p_sel.get("equipo_recibido_canje", "Ninguno")
                    c_col = p_sel.get("canje_color", "")
                    c_bat = p_sel.get("canje_bateria", "")
                    c_imei = p_sel.get("canje_imei", "")
                    c_val = float(p_sel.get("cotizacion_canje", 0.0))
                    
                    if c_mod != "Ninguno" and c_val > 0:
                        supabase.table("inventario").insert({
                            "modelo": str(c_mod), "color": str(c_col), "imei": str(c_imei), 
                            "condicion": "Usado", "bateria": str(c_bat), "costo_equipo": c_val, 
                            "precio_minorista": c_val + 150, "estado": "Disponible", "origen": "Canje"
                        }).execute()

                    supabase.table("pedidos").update({"estado": "Completado"}).eq("id", int(id_p_facturar)).execute()
                    
                    supabase.table("ventas").insert({
                        "cliente_nombre": str(p_sel["cliente_nombre"]), "vendedor_nombre": str(p_sel["vendedor_nombre"]),
                        "equipo_vendido": f"DESPACHO PEDIDO #{id_p_facturar}: {p_sel['equipos_reservados']}",
                        "precio_final_venta": float(p_sel["total_pedido"]) + c_val, "monto_abonado": float(p_sel["total_pedido"]),
                        "comision_vendedor": float(p_sel.get("comision_vendedor", 0.0)), "ganancia_neta_local": float(p_sel.get("ganancia_neta_local", 0.0)),
                        "comision_pagada": False, "equipo_recibido_canje": str(c_mod), "cotizacion_canje": c_val, "canje_imei": str(c_imei), "canje_bateria": str(c_bat),
                        "historial_pagos": [{"fecha": str(datetime.date.today()), "monto": float(p_sel["total_pedido"])}] if float(p_sel["total_pedido"]) > 0 else []
                    }).execute()
                    
                    st.success(f"🎉 ¡Pedido N° {id_p_facturar} despachado con éxito!")
                    st.rerun()

            with col_b3:
                if st.button("❌ ANULAR Y CANCELAR PEDIDO", use_container_width=True):
                    for eq_id in p_sel["ids_equipos"]:
                        supabase.table("inventario").update({"estado": "Disponible"}).eq("id", int(eq_id)).execute()
                    supabase.table("pedidos").delete().eq("id", int(id_p_facturar)).execute()
                    st.success(f"Pedido N° {id_p_facturar} anulado. Los celulares volvieron al mostrador.")
                    st.rerun()
    else:
        st.success("✨ No hay ningún pedido pendiente reteniendo stock. Todo el local está libre.")

# ----------------------------------------------------
# 4. HISTORIAL DE VENTAS CON REINTEGRO DE STOCK MEJORADO
# ----------------------------------------------------
with tab_historial:
    st.header("📜 Historial de Ventas")
    res_v = supabase.table("ventas").select("*").order("id", desc=True).execute()
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        df_v_show = df_v[["id", "fecha_venta", "equipo_vendido", "precio_final_venta", "monto_abonado", "cliente_nombre", "vendedor_nombre"]].copy()
        df_v_show["precio_final_venta"] = df_v_show["precio_final_venta"].apply(formato_dolares)
        df_v_show["monto_abonado"] = df_v_show["monto_abonado"].apply(formato_dolares)
        df_v_show.columns = ["ID Venta", "Fecha", "Equipos Vendidos e IMEIs", "Precio Venta", "Monto Abonado", "Cliente", "Vendedor"]
        st.dataframe(df_v_show, use_container_width=True, hide_index=True)

        # --- ANULAR Y ELIMINAR VENTA DEL HISTORIAL ---
        if es_admin:
            st.markdown("---")
            st.subheader("⚙️ Panel Administrativo de Anulación de Ventas")
            st.write("Si eliminas una venta, se borrará su registro de caja y comisiones de forma definitiva.")
            id_venta_borrar = st.selectbox("Seleccioná el ID de la venta que deseas anular y borrar:", df_v["id"].tolist(), key="sel_id_v_del")
            
            reintegrar_stock = st.checkbox("🔄 Reintegrar automáticamente los iPhones de esta venta de vuelta al Inventario (cambiar a Disponible)", value=True, key="reintegrar_stock")
            
            if st.button("🗑️ ANULAR Y ELIMINAR VENTA PERMANENTEMENTE", type="primary", use_container_width=True):
                v_sel = df_v[df_v["id"] == id_venta_borrar].iloc[0]
                
                if reintegrar_stock:
                    lista_imeis = re.findall(r"\[IMEI:\s*([^\]]+)\]", str(v_sel["equipo_vendido"]))
                    if lista_imeis:
                        supabase.table("inventario").update({"estado": "Disponible"}).in_("imei", lista_imeis).execute()
                        st.info(f"Se reingresaron {len(lista_imeis)} equipos al mostrador.")
                
                supabase.table("ventas").delete().eq("id", int(id_venta_borrar)).execute()
                st.success(f"Venta #{id_venta_borrar} anulada y eliminada del historial con éxito.")
                st.rerun()
    else: st.info("Sin registros.")

# ----------------------------------------------------
# 5. FINANZAS Y COMISIONES (ADMIN)
# ----------------------------------------------------
with tab_finanzas:
    if es_admin:
        st.header("💰 Liquidación de Comisiones y Reportes")
        f_in, f_fi = st.columns(2)
        f_d = f_in.date_input("Desde:", datetime.date.today().replace(day=1))
        f_h = f_fi.date_input("Hasta:", datetime.date.today())
        
        res_f = supabase.table("ventas").select("*").gte("fecha_venta", str(f_d)).lte("fecha_venta", str(f_h)).execute()
        if res_f.data:
            df_f = pd.DataFrame(res_f.data)
            df_f["comision_pagada"] = df_f["comision_pagada"].fillna(False)
            st.metric("Ganancia Neta Pura del Local (en este período)", formato_dolares(df_f["ganancia_neta_local"].sum()))
            
            st.markdown("---")
            st.subheader("🧑‍💼 Comisiones Pendientes")
            df_pendientes = df_f[df_f["comision_pagada"] == False]
            if not df_pendientes.empty:
                liq = df_pendientes.groupby("vendedor_nombre")["comision_vendedor"].sum().reset_index()
                st.dataframe(liq.style.format({"comision_vendedor": "${:,.2f}"}), use_container_width=True, hide_index=True)
                
                v_liq = st.selectbox("Sueldo a liquidar:", liq["vendedor_nombre"].tolist())
                if st.button("Marcar Comisiones como Pagadas"):
                    ids = df_pendientes[df_pendientes["vendedor_nombre"] == v_liq]["id"].tolist()
                    for idx in ids: supabase.table("ventas").update({"comision_pagada": True, "fecha_pago_comision": str(datetime.date.today())}).eq("id", int(idx)).execute()
                    st.success("Pagado.")
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
    else: st.error("🔒 Área exclusiva de administración.")

# ----------------------------------------------------
# 6. CLIENTES Y DEUDAS
# ----------------------------------------------------
with tab_clientes:
    st.header("👤 Cuentas Corrientes y Base de Clientes")
    clientes_list = traer_clientes()
    res_vtas = supabase.table("ventas").select("*").execute()
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        # --- PANEL DE EDICIÓN DE CLIENTE RESTAURADO ---
        st.subheader("✏️ Modificar Ficha de Cliente")
        if clientes_list:
            dic_cli = {c["nombre"]: c for c in clientes_list}
            sel_cli_ed = st.selectbox("Seleccionar Cliente a modificar:", list(dic_cli.keys()))
            cli_data = dic_cli[sel_cli_ed]
            
            upd_cli_nom = st.text_input("Nombre / Razón Social", value=cli_data["nombre"])
            upd_cli_tel = st.text_input("WhatsApp de Contacto", value=cli_data.get("contacto", ""))
            
            idx_tipo = ["Minorista", "Mayorista"].index(cli_data.get("tipo", "Minorista")) if cli_data.get("tipo") in ["Minorista", "Mayorista"] else 0
            upd_cli_tipo = st.selectbox("Categoría Comercial", ["Minorista", "Mayorista"], index=idx_tipo)
            
            if st.button("💾 Guardar Cambios de Cliente", use_container_width=True):
                supabase.table("clientes_ventas").update({
                    "nombre": upd_cli_nom, 
                    "contacto": upd_cli_tel, 
                    "tipo": upd_cli_tipo
                }).eq("id", cli_data["id"]).execute()
                
                # Sincronizamos las ventas para no perder la deuda si le cambia el nombre
                if upd_cli_nom != cli_data["nombre"]:
                    supabase.table("ventas").update({"cliente_nombre": upd_cli_nom}).eq("cliente_nombre", cli_data["nombre"]).execute()
                
                st.success("Ficha de cliente actualizada.")
                st.rerun()
        else:
            st.info("No hay clientes registrados en la base de datos.")

    with col_c2:
        st.subheader("💸 Cargar Cobro a Cuenta Corriente")
        if res_vtas.data:
            df_c = pd.DataFrame(res_vtas.data)
            df_c["Deuda"] = df_c["precio_final_venta"] - df_c["monto_abonado"]
            df_deudoras = df_c[df_c["Deuda"] > 0]
            
            if not df_deudoras.empty:
                opc_d = {f"Venta #{v['id']} - {v['cliente_nombre']} (Debe: {formato_dolares(v['Deuda'])})": v for _, v in df_deudoras.iterrows()}
                sel_v = st.selectbox("Cuenta a saldar:", list(opc_d.keys()))
                v_obj = opc_d[sel_v]
                n_cobro = st.number_input("Monto (U$S)", max_value=float(v_obj["Deuda"]), min_value=0.0)
                
                if st.button("Registrar Cobro", type="primary"):
                    h_p = v_obj.get("historial_pagos") or []
                    h_p.append({"fecha": str(datetime.date.today()), "monto": float(n_cobro)})
                    supabase.table("ventas").update({
                        "monto_abonado": float(v_obj["monto_abonado"]) + float(n_cobro), 
                        "historial_pagos": h_p
                    }).eq("id", int(v_obj["id"])).execute()
                    st.success("Cobrado y registrado en la cuenta corriente.")
                    st.rerun()
            else: st.success("Cuentas corrientes al día.")
            
    st.markdown("---")
    st.write("### 📊 Estado General de Cuentas")
    if res_vtas.data:
        resumen_cli = df_c.groupby("cliente_nombre").agg({"precio_final_venta":"sum", "monto_abonado":"sum", "Deuda":"sum"}).reset_index()
        resumen_cli.columns = ["Cliente", "Total Comprado", "Total Pagado", "Deuda Pendiente"]
        resumen_cli["Total Comprado"] = resumen_cli["Total Comprado"].apply(formato_dolares)
        resumen_cli["Total Pagado"] = resumen_cli["Total Pagado"].apply(formato_dolares)
        resumen_cli["Deuda Pendiente"] = resumen_cli["Deuda Pendiente"].apply(formato_dolares)
        st.dataframe(resumen_cli, hide_index=True, use_container_width=True)

# ----------------------------------------------------
# 7. PERSONAL VENDEDOR
# ----------------------------------------------------
with tab_directorio:
    if es_admin:
        st.header("👥 Gestión de Vendedores")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.subheader("➕ Nuevo Vendedor")
            n_v = st.text_input("Nombre completo:")
            if st.button("Dar de Alta Vendedor", type="primary"):
                if n_v:
                    supabase.table("vendedores").insert({"nombre": str(n_v)}).execute()
                    st.success(f"{n_v} agregado al equipo.")
                    st.rerun()
                    
        with col_v2:
            # --- PANEL DE GESTIÓN Y BAJA DE VENDEDORES RESTAURADO ---
            st.subheader("🗑️ Lista de Vendedores Activos")
            v_list = supabase.table("vendedores").select("*").execute().data
            if v_list:
                for v in v_list:
                    c_list1, c_list2 = st.columns([3, 1])
                    c_list1.write(f"🧑‍💼 **{v['nombre']}**")
                    if c_list2.button("Eliminar", key=f"del_vend_{v['id']}"):
                        supabase.table("vendedores").delete().eq("id", v['id']).execute()
                        st.warning(f"Vendedor eliminado.")
                        st.rerun()
            else:
                st.info("No hay vendedores cargados en el sistema.")
    else: st.error("🔒 Privado. Acceso exclusivo de administración.")
