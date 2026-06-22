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

# ==============================================================================
# INICIALIZACIÓN DE SESIÓN Y SEGURIDAD
# ==============================================================================
if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

es_admin = st.session_state.admin_auth

# ==============================================================================
# FUNCIONES AUXILIARES
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

def generar_presupuesto_pdf(cliente, equipos_nombres, subtotal, descuento, canje_info, valor_canje, total):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(150, 800, "ELECTRONIC - Presupuesto Comercial")
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}")
    c.drawString(50, 730, f"Cliente: {cliente}")
    c.line(50, 715, 550, 715)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 690, "Equipos a adquirir:")
    c.setFont("Helvetica", 11)
    y = 670
    for eq in equipos_nombres:
        c.drawString(60, y, f"- {eq}")
        y -= 20
        if y < 400: break
    
    y -= 10
    c.line(50, y, 550, y)
    y -= 25
    c.drawString(50, y, f"Subtotal Equipos: {formato_dolares(subtotal)}")
    if descuento > 0:
        y -= 20
        c.drawString(50, y, f"Descuentos Aplicados: - {formato_dolares(descuento)}")
    if valor_canje > 0:
        y -= 20
        c.drawString(50, y, f"Plan Canje a Favor ({canje_info}): - {formato_dolares(valor_canje)}")
        
    y -= 15
    c.line(50, y, 550, y)
    y -= 25
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"TOTAL A ABONAR: {formato_dolares(total)}")
    
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 100, "Este presupuesto es válido por 24 horas y está sujeto a disponibilidad de stock.")
    c.save()
    buffer.seek(0)
    return buffer

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
            else:
                st.error("Clave incorrecta")
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
    "📦 Inventario", "🤝 Venta y Canje", "📋 Historial", "💰 Finanzas", "👤 Clientes y Deudas", "👥 Directorio"
])

# ----------------------------------------------------
# 1. INVENTARIO
# ----------------------------------------------------
with tab_stock:
    st.header("Ingreso y Gestión de Mercadería")
    
    if es_admin:
        col1, col2, col3 = st.columns(3)
        with col1:
            mod_modelo = st.text_input("Modelo", placeholder="Ej: iPhone 15 Pro Max")
            mod_imei = st.text_input("IMEI")
            mod_condicion = st.selectbox("Condición", ["Sellado", "Usado", "CPO"])
            if mod_condicion == "Sellado":
                mod_bateria = "100%"
                st.info("Batería fijada al 100% por ser Sellado.")
            else:
                mod_bateria = st.text_input("Batería %", value="100%")
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
                    "modelo": mod_modelo, "imei": mod_imei, "condicion": mod_condicion, "bateria": mod_bateria,
                    "costo_equipo": cst_equipo, "costo_importacion": cst_carga, "costo_financiero": cst_finan,
                    "precio_super_mayorista": pr_super, "precio_mayorista": pr_mayo, "precio_minorista": pr_mino,
                    "estado": "Disponible"
                }
                supabase.table("inventario").insert(nuevo).execute()
                st.success("✅ Equipo ingresado correctamente.")
                st.rerun()
        st.markdown("---")
    else:
        st.info("🔒 Estás en Modo Vendedor. Solo el Administrador puede ingresar mercadería o editar costos.")

    st.subheader("📦 Stock Disponible en Local")
    res_stock = supabase.table("inventario").select("*").eq("estado", "Disponible").execute()
    if res_stock.data:
        df_stock = pd.DataFrame(res_stock.data)
        
        if es_admin:
            st.dataframe(df_stock[["id", "modelo", "condicion", "bateria", "imei", "costo_total", "precio_minorista"]], use_container_width=True, hide_index=True)
            
            st.markdown("### ✏️ Edición Avanzada de Stock")
            id_editar = st.selectbox("Seleccioná el ID del equipo a modificar:", df_stock["id"].tolist())
            if id_editar:
                eq_ed = df_stock[df_stock["id"] == id_editar].iloc[0]
                c_ed1, c_ed2, c_ed3 = st.columns(3)
                
                with c_ed1:
                    upd_mod = st.text_input("Modelo", value=eq_ed["modelo"], key="ue_m")
                    upd_imei = st.text_input("IMEI", value=eq_ed["imei"], key="ue_i")
                    idx_cond = ["Sellado", "Usado", "CPO"].index(eq_ed["condicion"]) if eq_ed["condicion"] in ["Sellado", "Usado", "CPO"] else 0
                    upd_cond = st.selectbox("Condición", ["Sellado", "Usado", "CPO"], index=idx_cond, key="ue_c")
                    if upd_cond == "Sellado":
                        upd_bat = "100%"
                    else:
                        upd_bat = st.text_input("Batería %", value=eq_ed.get("bateria", "100%"), key="ue_b")
                with c_ed2:
                    upd_cst_eq = st.number_input("Costo Eq", value=float(eq_ed["costo_equipo"]), key="ue_ce")
                    upd_cst_cg = st.number_input("Carga", value=float(eq_ed["costo_importacion"]), key="ue_cc")
                    upd_cst_fi = st.number_input("Interés", value=float(eq_ed["costo_financiero"]), key="ue_cf")
                with c_ed3:
                    upd_prs = st.number_input("Precio Super Mayo", value=float(eq_ed["precio_super_mayorista"]), key="ue_ps")
                    upd_prmayo = st.number_input("Precio Mayorista", value=float(eq_ed["precio_mayorista"]), key="ue_pma")
                    upd_prmino = st.number_input("Precio Minorista", value=float(eq_ed["precio_minorista"]), key="ue_pmi")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Guardar Cambios", type="primary"):
                        supabase.table("inventario").update({
                            "modelo": upd_mod, "imei": upd_imei, "condicion": upd_cond, "bateria": upd_bat,
                            "costo_equipo": upd_cst_eq, "costo_importacion": upd_cst_cg, "costo_financiero": upd_cst_fi,
                            "precio_super_mayorista": upd_prs, "precio_mayorista": upd_prmayo, "precio_minorista": upd_prmino
                        }).eq("id", int(id_editar)).execute()
                        st.success("Equipo actualizado.")
                        st.rerun()
        else:
            df_vendedor = df_stock[["modelo", "condicion", "bateria", "imei", "precio_minorista"]].copy()
            df_vendedor["precio_minorista"] = df_vendedor["precio_minorista"].apply(formato_dolares)
            df_vendedor.columns = ["Modelo", "Condición", "Batería", "IMEI", "Precio Público (U$S)"]
            st.dataframe(df_vendedor, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay equipos disponibles en stock.")

# ----------------------------------------------------
# 2. VENTA, CANJE Y PRESUPUESTO
# ----------------------------------------------------
with tab_venta:
    st.header("🤝 Armar Operación")
    
    equipos_disp = supabase.table("inventario").select("*").eq("estado", "Disponible").execute().data or []
    clientes_list = supabase.table("clientes_ventas").select("*").execute().data or []
    vendedores_list = supabase.table("vendedores").select("*").execute().data or []
    
    if not equipos_disp: 
        st.warning("No hay equipos en stock.")
    else:
        st.subheader("1. Selección de Equipos")
        opciones_eq = {f"{e['modelo']} ({e.get('bateria', '100%')}) - IMEI: {e['imei']} - {formato_dolares(e['precio_minorista'])}": e for e in equipos_disp}
        seleccionados_keys = st.multiselect("Buscá y seleccioná uno o varios equipos:", list(opciones_eq.keys()))
        
        if seleccionados_keys:
            equipos_seleccionados = [opciones_eq[k] for k in seleccionados_keys]
            nombres_equipos = [e["modelo"] for e in equipos_seleccionados]
            subtotal_minorista = sum(float(e["precio_minorista"]) for e in equipos_seleccionados)
            subtotal_supermayo = sum(float(e["precio_super_mayorista"]) for e in equipos_seleccionados)
            costo_total_lote = sum(float(e["costo_total"]) for e in equipos_seleccionados)
            
            st.info(f"🛒 Lote armado: **{len(equipos_seleccionados)} equipos**. Subtotal inicial: **{formato_dolares(subtotal_minorista)}**")
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.subheader("2. Cliente y Vendedor")
                tipo_cli = st.radio("Cliente:", ["Existente", "Nuevo"], horizontal=True)
                if tipo_cli == "Existente" and clientes_list:
                    cliente_final = st.selectbox("Cliente:", [c["nombre"] for c in clientes_list])
                else:
                    cliente_final = st.text_input("Nombre del Nuevo Cliente:")
                    tel_cli = st.text_input("WhatsApp (Ej: 381...):")
                    tipo_categoria = st.selectbox("Categoría:", ["Minorista", "Mayorista"])
                
                sel_vendedor = ""
                if vendedores_list:
                    sel_vendedor = st.selectbox("Vendedor a cargo:", [v["nombre"] for v in vendedores_list])
                else:
                    st.warning("Agregá al menos un vendedor en la pestaña 'Directorio'.")
                
                st.subheader("3. Descuentos Aplicados")
                descuento_manual = st.number_input("Descuento Manual (U$S)", min_value=0.0, step=10.0)
                descuento_lote = 0.0
                if len(equipos_seleccionados) >= 10:
                    descuento_lote = len(equipos_seleccionados) * 5.0
                    st.success(f"🔥 Descuento por lote automático aplicado: -{formato_dolares(descuento_lote)} (U$S 5 por equipo)")
                descuento_total = descuento_manual + descuento_lote

            with col_v2:
                st.subheader("4. Plan Canje")
                hay_canje = st.toggle("Activar Ingreso de Usado")
                canje_mod = canje_bat = canje_imei = ""
                valor_canje = 0.0
                if hay_canje:
                    with st.container(border=True):
                        canje_mod = st.text_input("Modelo del Usado", placeholder="Ej: iPhone 13 128GB")
                        c_bat, c_imei = st.columns(2)
                        canje_bat = c_bat.text_input("Batería %")
                        canje_imei = c_imei.text_input("IMEI Usado")
                        valor_canje = st.number_input("Cotización a favor del cliente (U$S)", min_value=0.0, step=10.0)

            total_venta = subtotal_minorista - descuento_total - valor_canje
            
            st.markdown("---")
            st.subheader("5. Cobro y Cierre")
            st.metric("TOTAL FINAL A ABONAR POR EL CLIENTE", formato_dolares(total_venta))
            monto_abonado = st.number_input("¿Cuánto abonó el cliente en este momento? (U$S)", min_value=0.0, max_value=float(total_venta), value=float(total_venta), step=10.0)
            
            comision_calculada = (subtotal_minorista - descuento_total) - subtotal_supermayo
            ganancia_local = subtotal_supermayo - costo_total_lote

            st.write("### 🧮 Resumen Financiero")
            res_col1, res_col2 = st.columns(2)
            if sel_vendedor:
                res_col1.metric(f"Comisión calculada para {sel_vendedor}", formato_dolares(comision_calculada))
            if es_admin:
                res_col2.metric("Ganancia Neta del Local (Modo Admin)", formato_dolares(ganancia_local))
            else:
                res_col2.info("🔒 Ganancia del local oculta en Modo Vendedor.")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("📄 EMITIR PRESUPUESTO (PDF)", use_container_width=True):
                    info_canje = f"{canje_mod} {canje_bat}" if hay_canje else ""
                    pdf = generar_presupuesto_pdf(cliente_final, nombres_equipos, subtotal_minorista, descuento_total, info_canje, valor_canje, total_venta)
                    st.download_button("Descargar Presupuesto Oficial", pdf, f"Presupuesto_{cliente_final}.pdf", "application/pdf", use_container_width=True)
            with b2:
                if st.button("✅ REGISTRAR VENTA OFICIAL", type="primary", use_container_width=True):
                    if cliente_final and sel_vendedor:
                        if tipo_cli == "Nuevo":
                            supabase.table("clientes_ventas").insert({"nombre": cliente_final, "contacto": tel_cli, "tipo": tipo_categoria}).execute()

                        nombres_str = ", ".join(nombres_equipos)
                        for eq in equipos_seleccionados:
                            supabase.table("inventario").update({"estado": "Vendido"}).eq("id", eq['id']).execute()
                        
                        if hay_canje and canje_mod:
                            eq_canje = {
                                "modelo": f"CANJE: {canje_mod}", "imei": canje_imei, "condicion": "Usado", "bateria": canje_bat,
                                "costo_equipo": valor_canje, "costo_importacion": 0, "costo_financiero": 0,
                                "precio_super_mayorista": valor_canje + 50, "precio_mayorista": valor_canje + 100, "precio_minorista": valor_canje + 150,
                                "estado": "Disponible"
                            }
                            supabase.table("inventario").insert(eq_canje).execute()

                        # Iniciar historial de pagos
                        historial_p = []
                        if monto_abonado > 0:
                            historial_p.append({"fecha": str(datetime.date.today()), "monto": float(monto_abonado)})

                        nueva_venta = {
                            "cliente_nombre": cliente_final, "vendedor_nombre": sel_vendedor,
                            "equipo_vendido": nombres_str, "precio_final_venta": subtotal_minorista - descuento_total,
                            "descuento_aplicado": descuento_total,
                            "equipo_recibido_canje": canje_mod if hay_canje else "Ninguno",
                            "canje_imei": canje_imei, "canje_bateria": canje_bat, "cotizacion_canje": valor_canje,
                            "monto_abonado": monto_abonado,
                            "historial_pagos": historial_p,
                            "comision_vendedor": comision_calculada, "ganancia_neta_local": ganancia_local,
                            "comision_pagada": False
                        }
                        supabase.table("ventas").insert(nueva_venta).execute()
                        st.success("🎉 ¡Venta registrada exitosamente!")
                    else:
                        st.error("Falta nombre del cliente o asignar un vendedor.")

# ----------------------------------------------------
# 3. HISTORIAL
# ----------------------------------------------------
with tab_historial:
    st.header("📋 Historial de Operaciones")
    res_v = supabase.table("ventas").select("*").order("id", desc=True).execute()
    if res_v.data:
        df_v = pd.DataFrame(res_v.data)
        df_v_show = df_v[["fecha_venta", "equipo_vendido", "precio_final_venta", "equipo_recibido_canje", "monto_abonado", "cliente_nombre", "vendedor_nombre"]].copy()
        df_v_show["precio_final_venta"] = df_v_show["precio_final_venta"].apply(formato_dolares)
        df_v_show["monto_abonado"] = df_v_show["monto_abonado"].apply(formato_dolares)
        st.dataframe(df_v_show, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 4. FINANZAS Y COMISIONES (ADMIN)
# ----------------------------------------------------
with tab_finanzas:
    if es_admin:
        st.header("💰 Finanzas, Caja y Liquidaciones")
        
        # Filtros de fecha
        st.subheader("📅 Filtro de Fechas")
        f_inicio, f_fin = st.columns(2)
        fecha_desde = f_inicio.date_input("Desde:", datetime.date.today().replace(day=1))
        fecha_hasta = f_fin.date_input("Hasta:", datetime.date.today())
        
        res_f = supabase.table("ventas").select("*").gte("fecha_venta", str(fecha_desde)).lte("fecha_venta", str(fecha_hasta)).execute()
        
        if res_f.data:
            df_f = pd.DataFrame(res_f.data)
            df_f["comision_pagada"] = df_f["comision_pagada"].fillna(False)
            
            st.metric("Ganancia Neta Pura del Local (en este período)", formato_dolares(df_f["ganancia_neta_local"].sum()))
            st.markdown("---")
            
            st.subheader("🧑‍💼 Comisiones a Pagar por Vendedor")
            
            df_pendientes = df_f[df_f["comision_pagada"] == False]
            if not df_pendientes.empty:
                liq = df_pendientes.groupby("vendedor_nombre")["comision_vendedor"].sum().reset_index()
                liq.columns = ["Vendedor", "Comisión Pendiente a Pagar"]
                
                col_liq1, col_liq2 = st.columns(2)
                with col_liq1:
                    st.dataframe(liq.style.format({"Comisión Pendiente a Pagar": "${:,.2f}"}), hide_index=True, use_container_width=True)
                with col_liq2:
                    st.write("✅ **Liquidar Comisiones**")
                    vend_a_pagar = st.selectbox("Seleccionar Vendedor a Liquidar:", liq["Vendedor"].tolist())
                    if st.button("Marcar Comisiones Pendientes como Pagadas", type="primary"):
                        # Marcar ventas pendientes de este vendedor como pagadas
                        ids_a_pagar = df_pendientes[df_pendientes["vendedor_nombre"] == vend_a_pagar]["id"].tolist()
                        for id_v in ids_a_pagar:
                            supabase.table("ventas").update({"comision_pagada": True, "fecha_pago_comision": str(datetime.date.today())}).eq("id", id_v).execute()
                        st.success(f"¡Comisiones de {vend_a_pagar} liquidadas correctamente!")
                        st.rerun()
            else:
                st.success("✅ Todas las comisiones de este período están pagadas.")
                
            st.markdown("---")
            st.subheader("📚 Historial de Comisiones ya Pagadas")
            df_pagadas = df_f[df_f["comision_pagada"] == True]
            if not df_pagadas.empty:
                df_hist_comis = df_pagadas[["fecha_pago_comision", "vendedor_nombre", "equipo_vendido", "comision_vendedor"]].copy()
                df_hist_comis["comision_vendedor"] = df_hist_comis["comision_vendedor"].apply(formato_dolares)
                df_hist_comis.columns = ["Fecha de Pago", "Vendedor", "Venta Originaria", "Monto"]
                st.dataframe(df_hist_comis, hide_index=True, use_container_width=True)
            else:
                st.info("Aún no hay registros de comisiones pagadas en este período.")

        else:
            st.info("No hay ventas registradas en el rango de fechas seleccionado.")
    else:
        st.error("🔒 **Acceso Denegado:** Esta pestaña requiere permisos de Administrador.")

# ----------------------------------------------------
# 5. CLIENTES Y DEUDAS
# ----------------------------------------------------
with tab_clientes:
    st.header("👤 Estado de Clientes, Deudas y Cobranzas")
    
    clientes_list = supabase.table("clientes_ventas").select("*").execute().data or []
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.subheader("✏️ Editar Cliente Existente")
        if clientes_list:
            dic_cli = {c["nombre"]: c for c in clientes_list}
            sel_cli_ed = st.selectbox("Seleccionar Cliente:", list(dic_cli.keys()))
            cli_data = dic_cli[sel_cli_ed]
            
            upd_cli_nom = st.text_input("Nombre / Razón Social", value=cli_data["nombre"])
            upd_cli_tel = st.text_input("WhatsApp", value=cli_data.get("contacto", ""))
            idx_tipo = ["Minorista", "Mayorista"].index(cli_data.get("tipo", "Minorista")) if cli_data.get("tipo") in ["Minorista", "Mayorista"] else 0
            upd_cli_tipo = st.selectbox("Categoría", ["Minorista", "Mayorista"], index=idx_tipo)
            
            if st.button("Guardar Cambios del Cliente"):
                # Actualizamos la tabla clientes
                supabase.table("clientes_ventas").update({
                    "nombre": upd_cli_nom, "contacto": upd_cli_tel, "tipo": upd_cli_tipo
                }).eq("id", cli_data["id"]).execute()
                
                # Si cambió el nombre, actualizamos el historial de ventas para que no se pierdan los registros
                if upd_cli_nom != cli_data["nombre"]:
                    supabase.table("ventas").update({"cliente_nombre": upd_cli_nom}).eq("cliente_nombre", cli_data["nombre"]).execute()
                    
                st.success("Cliente actualizado.")
                st.rerun()
                
    with col_c2:
        st.subheader("💸 Cargar Pago de Cliente")
        res_vtas = supabase.table("ventas").select("*").execute()
        if res_vtas.data:
            df_v = pd.DataFrame(res_vtas.data)
            df_v["Deuda"] = df_v["efectivo_a_cobrar"] - df_v["monto_abonado"]
            
            # Solo traemos las ventas que tienen deuda
            df_deudoras = df_v[df_v["Deuda"] > 0]
            if not df_deudoras.empty:
                opciones_deuda = {f"Venta #{v['id']} - {v['cliente_nombre']} - Deuda: {formato_dolares(v['Deuda'])}": v for _, v in df_deudoras.iterrows()}
                sel_v_deuda = st.selectbox("Seleccionar Cuenta Corriente a saldar:", list(opciones_deuda.keys()))
                v_obj = opciones_deuda[sel_v_deuda]
                
                nuevo_cobro = st.number_input("Ingresar Pago Recibido (U$S)", min_value=0.0, max_value=float(v_obj["Deuda"]), step=10.0)
                
                if st.button("Registrar Pago Oficial", type="primary"):
                    historial_p = v_obj.get("historial_pagos") or []
                    historial_p.append({"fecha": str(datetime.date.today()), "monto": float(nuevo_cobro)})
                    nuevo_monto_ab = float(v_obj["monto_abonado"]) + float(nuevo_cobro)
                    
                    supabase.table("ventas").update({
                        "monto_abonado": nuevo_monto_ab,
                        "historial_pagos": historial_p
                    }).eq("id", v_obj["id"]).execute()
                    
                    st.success("¡Pago ingresado correctamente!")
                    st.rerun()
            else:
                st.success("No hay deudas pendientes para cobrar.")

    st.markdown("---")
    st.write("### 📊 Historial General y Estado de Cuenta")
    if res_vtas.data:
        resumen_cli = df_v.groupby("cliente_nombre").agg({"efectivo_a_cobrar":"sum", "monto_abonado":"sum", "Deuda":"sum"}).reset_index()
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
        st.header("👥 Gestión de Vendedores")
        nuevo_vend = st.text_input("Ingresar nombre del Vendedor:")
        if st.button("Agregar Vendedor", type="primary"):
            if nuevo_vend:
                supabase.table("vendedores").insert({"nombre": nuevo_vend}).execute()
                st.success("Agregado.")
                st.rerun()
        v_list = supabase.table("vendedores").select("*").execute().data
        if v_list:
            st.dataframe(pd.DataFrame(v_list)[["nombre"]], hide_index=True, use_container_width=True)
    else:
        st.error("🔒 **Acceso Denegado:** Solo el administrador puede agregar o eliminar personal del sistema.")
