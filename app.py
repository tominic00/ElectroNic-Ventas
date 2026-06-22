import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import requests

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Ventas iPhone ERP", layout="wide", initial_sidebar_state="expanded")

# --- CONFIGURACIÓN DE CONEXIÓN A SUPABASE ---
SUPABASE_URL = "https://orligvvuajntokqxtajy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ybGlndnZ1YWpudG9rcXh0YWp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE4OTg3MTksImV4cCI6MjA5NzQ3NDcxOX0.9zewrwO1nrXIbp-Nx-x5hL1qVA28ZQDO7I2UgzjwQiA"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error al inicializar cliente Supabase: {e}")

# ==============================================================================
# FUNCIONES AUXILIARES Y DE FORMATO
# ==============================================================================
def formato_dolares(valor):
    try:
        monto = f"{float(valor):,.2f}"
        return "U$S " + monto.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "U$S 0,00"

# Extracción de Dólar Blue en tiempo real (API robusta)
@st.cache_data(ttl=300) # Se actualiza cada 5 minutos automáticamente
def obtener_dolar_blue():
    try:
        r = requests.get("https://dolarapi.com/v1/dolares/blue", timeout=5)
        data = r.json()
        return data["compra"], data["venta"]
    except:
        return 1000.0, 1000.0 # Valor de respaldo en caso de no tener internet

dolar_compra, dolar_venta = obtener_dolar_blue()

# ==============================================================================
# BARRA LATERAL: CALCULADORA ARS -> USD
# ==============================================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg", width=60)
    st.title("Electronic Ventas")
    st.markdown("---")
    
    st.subheader("💵 Cotización Dólar Blue")
    st.metric("Compra (Te pagan con billete)", f"$ {dolar_compra:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("Venta (Vos comprás billete)", f"$ {dolar_venta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    st.markdown("---")
    st.subheader("🧮 Calculadora de Cobro")
    st.write("Convertí pagos en Pesos a Dólares.")
    
    monto_pesos = st.number_input("Monto en Pesos (ARS)", min_value=0.0, step=1000.0)
    tipo_cotizacion = st.radio("Usar cotización de:", ["Compra", "Venta"])
    
    tasa_usar = dolar_compra if tipo_cotizacion == "Compra" else dolar_venta
    
    if monto_pesos > 0:
        conversion = monto_pesos / tasa_usar
        st.success(f"Equivale a:\n### {formato_dolares(conversion)}")

# ==============================================================================
# PANTALLA PRINCIPAL Y PESTAÑAS
# ==============================================================================
st.title("🍏 Electronic — ERP de Ventas e Importación")
st.markdown("---")

tab_stock, tab_venta, tab_historial, tab_finanzas, tab_directorio = st.tabs([
    "📦 Inventario de Equipos", "🤝 Venta y Plan Canje", "📋 Historial de Ventas", "💰 Liquidación y Comisiones", "👥 Directorio"
])

# ----------------------------------------------------
# 1. INVENTARIO (INGRESO Y STOCK)
# ----------------------------------------------------
with tab_stock:
    st.header("Ingreso de Mercadería (Importación)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("1. Equipo")
        mod_modelo = st.text_input("Modelo de iPhone", placeholder="Ej: iPhone 15 Pro Max 256GB")
        mod_imei = st.text_input("IMEI / Número de Serie")
        mod_condicion = st.selectbox("Condición", ["Sellado", "Usado", "CPO (Reacondicionado)"])
        
    with col2:
        st.subheader("2. Costos de Origen (U$S)")
        cst_equipo = st.number_input("Costo del Equipo", min_value=0.0, step=10.0)
        cst_carga = st.number_input("Costo de Carga (EEUU-TUC)", min_value=0.0, step=5.0)
        cst_finan = st.number_input("Intereses / Costo Financiero", min_value=0.0, step=5.0)
        st.info(f"Costo Total Real: **{formato_dolares(cst_equipo + cst_carga + cst_finan)}**")
        
    with col3:
        st.subheader("3. Lista de Precios (U$S)")
        pr_super = st.number_input("Precio Super Mayorista (Base Comisionista)", min_value=0.0, step=10.0)
        pr_mayo = st.number_input("Precio Mayorista", min_value=0.0, step=10.0)
        pr_mino = st.number_input("Precio Minorista (Público)", min_value=0.0, step=10.0)

    if st.button("📥 GUARDAR EQUIPO EN INVENTARIO", type="primary", use_container_width=True):
        if mod_modelo and mod_imei:
            nuevo_equipo = {
                "modelo": mod_modelo, "imei": mod_imei, "condicion": mod_condicion,
                "costo_equipo": cst_equipo, "costo_importacion": cst_carga, "costo_financiero": cst_finan,
                "precio_super_mayorista": pr_super, "precio_mayorista": pr_mayo, "precio_minorista": pr_mino,
                "estado": "Disponible"
            }
            try:
                supabase.table("inventario").insert(nuevo_equipo).execute()
                st.success(f"✅ iPhone {mod_modelo} (IMEI: {mod_imei}) ingresado correctamente al stock.")
            except Exception as e:
                st.error(f"Error al guardar (¿El IMEI ya existe?): {e}")
        else:
            st.warning("Completá Modelo e IMEI.")

    st.markdown("---")
    st.subheader("📦 Stock Disponible en Local")
    res_stock = supabase.table("inventario").select("*").eq("estado", "Disponible").execute()
    if res_stock.data:
        df_stock = pd.DataFrame(res_stock.data)
        st.dataframe(df_stock[["id", "fecha_ingreso", "modelo", "imei", "condicion", "costo_total", "precio_super_mayorista", "precio_minorista"]], hide_index=True, use_container_width=True)
    else:
        st.info("El inventario está vacío o no hay equipos disponibles.")

# ----------------------------------------------------
# 2. VENTA Y PLAN CANJE
# ----------------------------------------------------
with tab_venta:
    st.header("Registrar Nueva Venta")
    
    # Traer data de la nube
    equipos_disp = supabase.table("inventario").select("*").eq("estado", "Disponible").execute().data or []
    clientes_list = supabase.table("clientes_ventas").select("*").execute().data or []
    vendedores_list = supabase.table("vendedores").select("*").execute().data or []
    
    if not equipos_disp:
        st.warning("⚠️ No hay equipos en stock para vender.")
    elif not vendedores_list:
        st.warning("⚠️ Primero debes registrar al menos un Vendedor en la pestaña 'Directorio'.")
    else:
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.subheader("🛍️ Datos de la Operación")
            
            # Selector de Equipo
            dic_equipos = {f"{e['modelo']} - IMEI: {e['imei']} (Min: {formato_dolares(e['precio_minorista'])})": e for e in equipos_disp}
            sel_equipo_key = st.selectbox("Equipo a Vender:", list(dic_equipos.keys()))
            equipo_seleccionado = dic_equipos[sel_equipo_key]
            
            # Mostrar costos internos del equipo
            st.info(f"💡 Base (Precio Super Mayorista): {formato_dolares(equipo_seleccionado['precio_super_mayorista'])}")
            
            # Selector Vendedor
            sel_vendedor = st.selectbox("Vendedor (Quien cerró la operación):", [v["nombre"] for v in vendedores_list])
            
            # Cliente
            tipo_ingreso_cli = st.radio("Cliente:", ["Existente", "Nuevo"], horizontal=True)
            if tipo_ingreso_cli == "Existente" and clientes_list:
                sel_cli = st.selectbox("Seleccionar Cliente:", [c["nombre"] for c in clientes_list])
                cliente_final = sel_cli
            else:
                nuevo_cli = st.text_input("Nombre del Cliente Nuevo:")
                tel_cli = st.text_input("Teléfono (Opcional):")
                tipo_cli = st.selectbox("Tipo de Cliente:", ["Minorista", "Mayorista"])
                cliente_final = nuevo_cli
                
            precio_cierre = st.number_input("Precio Final de Venta Cerrado (U$S)", value=float(equipo_seleccionado['precio_minorista']), step=10.0)

        with col_v2:
            st.subheader("🔄 Plan Canje (Opcional)")
            st.write("¿El cliente entrega un equipo en parte de pago?")
            hay_canje = st.toggle("Activar Plan Canje")
            
            equipo_recibido = ""
            valor_canje = 0.0
            
            if hay_canje:
                st.container(border=True)
                equipo_recibido = st.text_input("¿Qué iPhone deja el cliente? (Modelo, GB, Batería %)")
                valor_canje = st.number_input("Cotización del Usado (A favor del cliente U$S)", min_value=0.0, step=10.0)
                
                if equipo_recibido and valor_canje > 0:
                    st.success(f"Efectivo final a cobrar al cliente: **{formato_dolares(precio_cierre - valor_canje)}**")
        
        st.markdown("---")
        
        # Matemática de Comisiones y Ganancias
        comision_calculada = precio_cierre - float(equipo_seleccionado['precio_super_mayorista'])
        ganancia_local = float(equipo_seleccionado['precio_super_mayorista']) - float(equipo_seleccionado['costo_total'])
        
        st.write("### 🧮 Resumen Financiero Interno de la Venta")
        res1, res2, res3 = st.columns(3)
        res1.metric("Efectivo a Recibir (Caja)", formato_dolares(precio_cierre - valor_canje))
        res2.metric(f"Comisión para {sel_vendedor}", formato_dolares(comision_calculada))
        res3.metric("Ganancia Neta del Local", formato_dolares(ganancia_local))

        if st.button("✅ CONFIRMAR Y REGISTRAR VENTA", type="primary", use_container_width=True):
            if not cliente_final:
                st.error("Por favor, ingresá o seleccioná un cliente.")
            else:
                # 1. Guardar cliente nuevo si hace falta
                if tipo_ingreso_cli == "Nuevo" and cliente_final:
                    supabase.table("clientes_ventas").insert({"nombre": cliente_final, "contacto": tel_cli, "tipo": tipo_cli}).execute()

                # 2. Actualizar estado del equipo en Inventario a "Vendido"
                supabase.table("inventario").update({"estado": "Vendido"}).eq("id", equipo_seleccionado['id']).execute()
                
                # 3. (Opcional Automático) Si hay canje, ingresar el usado al inventario a costo 0 de carga, costo equipo = valor de canje
                if hay_canje and equipo_recibido:
                    equipo_canje_inv = {
                        "modelo": f"CANJE: {equipo_recibido}", "imei": "A Cargar", "condicion": "Usado",
                        "costo_equipo": valor_canje, "costo_importacion": 0, "costo_financiero": 0,
                        "precio_super_mayorista": valor_canje + 50, # Margen base automático
                        "precio_mayorista": valor_canje + 100, 
                        "precio_minorista": valor_canje + 150,
                        "estado": "Disponible"
                    }
                    supabase.table("inventario").insert(equipo_canje_inv).execute()

                # 4. Registrar la Venta oficial
                nueva_venta = {
                    "cliente_nombre": cliente_final,
                    "vendedor_nombre": sel_vendedor,
                    "equipo_vendido": f"{equipo_seleccionado['modelo']} (IMEI: {equipo_seleccionado['imei']})",
                    "precio_final_venta": precio_cierre,
                    "equipo_recibido_canje": equipo_recibido if hay_canje else "Ninguno",
                    "cotizacion_canje": valor_canje,
                    "comision_vendedor": comision_calculada,
                    "ganancia_neta_local": ganancia_local
                }
                
                supabase.table("ventas").insert(nueva_venta).execute()
                st.success("🎉 ¡Operación Exitosa! Venta registrada, comisiones liquidadas e inventario actualizado.")
                st.rerun()

# ----------------------------------------------------
# 3. HISTORIAL DE VENTAS
# ----------------------------------------------------
with tab_historial:
    st.header("📋 Historial de Operaciones")
    res_ventas = supabase.table("ventas").select("*").order("id", desc=True).execute()
    
    if res_ventas.data:
        df_v = pd.DataFrame(res_ventas.data)
        
        # Formateo visual
        df_v_show = df_v[["fecha_venta", "equipo_vendido", "precio_final_venta", "equipo_recibido_canje", "efectivo_a_cobrar", "cliente_nombre", "vendedor_nombre"]].copy()
        df_v_show["precio_final_venta"] = df_v_show["precio_final_venta"].apply(formato_dolares)
        df_v_show["efectivo_a_cobrar"] = df_v_show["efectivo_a_cobrar"].apply(formato_dolares)
        
        df_v_show.columns = ["Fecha", "Equipo Vendido", "Precio Venta", "Canje Recibido", "Efectivo Cobrado", "Cliente", "Vendedor"]
        st.dataframe(df_v_show, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay ventas registradas.")

# ----------------------------------------------------
# 4. FINANZAS Y COMISIONES (LIQUIDACIÓN DE SUELDOS)
# ----------------------------------------------------
with tab_finanzas:
    st.header("💰 Liquidación de Comisiones y Ganancias del Local")
    
    res_finanzas = supabase.table("ventas").select("*").execute()
    if res_finanzas.data:
        df_f = pd.DataFrame(res_finanzas.data)
        
        ganancia_total_local = df_f["ganancia_neta_local"].sum()
        total_comisiones_repartidas = df_f["comision_vendedor"].sum()
        
        st.subheader("📊 Balance General de Rentabilidad")
        col_b1, col_b2 = st.columns(2)
        col_b1.metric("Ganancia Neta Total del Local (U$S Limpios)", formato_dolares(ganancia_total_local))
        col_b2.metric("Total en Comisiones Generadas por Vendedores", formato_dolares(total_comisiones_repartidas))
        
        st.markdown("---")
        st.subheader("🧑‍💼 Liquidación de Sueldos por Vendedor")
        st.write("Acumulado de comisiones (Diferencia entre Precio de Venta y Precio Super Mayorista).")
        
        # Agrupamos por vendedor y sumamos sus comisiones
        liq_vendedores = df_f.groupby("vendedor_nombre")["comision_vendedor"].sum().reset_index()
        liq_vendedores.columns = ["Vendedor", "Comisiones Acumuladas a Pagar"]
        liq_vendedores["Comisiones Acumuladas a Pagar"] = liq_vendedores["Comisiones Acumuladas a Pagar"].apply(formato_dolares)
        
        st.dataframe(liq_vendedores, hide_index=True, use_container_width=True)
    else:
        st.info("No hay datos financieros disponibles todavía.")

# ----------------------------------------------------
# 5. DIRECTORIO (CLIENTES Y VENDEDORES)
# ----------------------------------------------------
with tab_directorio:
    st.header("👥 Gestión de Directorio")
    
    col_dir1, col_dir2 = st.columns(2)
    
    with col_dir1:
        st.subheader("🧑‍💼 Vendedores del Local")
        nuevo_vend = st.text_input("Ingresar nombre del Vendedor:")
        if st.button("Agregar Vendedor", type="primary"):
            if nuevo_vend:
                supabase.table("vendedores").insert({"nombre": nuevo_vend}).execute()
                st.success("Vendedor agregado.")
                st.rerun()
                
        vend_list = supabase.table("vendedores").select("*").execute().data
        if vend_list:
            df_vend = pd.DataFrame(vend_list)
            st.dataframe(df_vend[["nombre"]], hide_index=True, use_container_width=True)
            
    with col_dir2:
        st.subheader("🤝 Clientes")
        cli_list = supabase.table("clientes_ventas").select("*").execute().data
        if cli_list:
            df_cli = pd.DataFrame(cli_list)
            st.dataframe(df_cli[["nombre", "contacto", "tipo"]], hide_index=True, use_container_width=True)
