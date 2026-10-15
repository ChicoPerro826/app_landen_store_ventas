import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Configuración de la página para celulares
st.set_page_config(page_title="Landen Store - Control de Ventas", page_icon="🧴", layout="centered")

# --- CONEXIÓN A BASE DE DATOS LOCAL ---
def get_connection():
    conn = sqlite3.connect("landen_store.db")
    return conn

def init_sqlite():
    conn = get_connection()
    c = conn.cursor()
    # Tabla de Catálogo
    c.execute('''
        CREATE TABLE IF NOT EXISTS catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT,
            tipo TEXT,
            producto TEXT UNIQUE,
            precio_usd REAL
        )
    ''')
    # Tabla de Ventas
    c.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            marca TEXT,
            producto TEXT,
            cliente TEXT,
            tipo_cliente TEXT,
            cantidad INTEGER,
            precio_unitario_usd REAL,
            total_usd REAL,
            metodo_pago TEXT,
            notas TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_sqlite()

# --- ENCABEZADO Y ESTILO ---
st.title("🧴 Landen Store")
st.caption("Sistema de Gestión de Ventas & Catálogo")

tabs = st.tabs(["🛒 Nueva Venta", "📊 Panel & Métricas", "📦 Catálogo / Excel", "📥 Exportar Ventas"])

# ---------------------------------------------------------
# TAB 1: REGISTRAR NUEVA VENTA
# ---------------------------------------------------------
with tabs[0]:
    st.header("Registrar Venta")
    
    conn = get_connection()
    df_cat = pd.read_sql_query("SELECT * FROM catalogo", conn)
    conn.close()

    if df_cat.empty:
        st.warning("⚠️ El catálogo está vacío. Cargá tu archivo Excel en la pestaña 'Catálogo / Excel' para empezar.")
    else:
        marcas = sorted(df_cat['marca'].unique().tolist())
        marca_sel = st.selectbox("Marca", marcas)

        prods_marca = df_cat[df_cat['marca'] == marca_sel]
        prod_names = sorted(prods_marca['producto'].unique().tolist())
        producto_sel = st.selectbox("Producto / Perfume", prod_names)

        # Buscar precio sugerido
        precio_sugerido = prods_marca[prods_marca['producto'] == producto_sel]['precio_usd'].values[0]

        col1, col2 = st.columns(2)
        with col1:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
        with col2:
            precio_unitario = st.number_input("Precio de Venta ($ USD)", value=float(precio_sugerido), step=1.0)

        total = cantidad * precio_unitario
        st.info(f"**Total a cobrar:** ${total:.2f} USD")

        st.divider()

        cliente = st.text_input("Nombre del Cliente", placeholder="Ej: Lucas")
        tipo_cliente = st.radio("Tipo de Cliente", ["Minorista", "Mayorista"], horizontal=True)
        metodo_pago = st.selectbox("Método de Pago", ["Efectivo USD", "Efectivo ARS", "Transferencia", "Mercado Pago", "Otro"])
        notas = st.text_input("Notas / Observaciones", placeholder="Opcional (ej: seña, entrega pendiente)")

        if st.button("✅ Registrar Venta", type="primary", use_container_width=True):
            if not cliente.strip():
                st.error("Por favor ingresá el nombre del cliente.")
            else:
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO ventas (fecha, marca, producto, cliente, tipo_cliente, cantidad, precio_unitario_usd, total_usd, metodo_pago, notas)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fecha_actual, marca_sel, producto_sel, cliente, tipo_cliente, cantidad, precio_unitario, total, metodo_pago, notas))
                conn.commit()
                conn.close()
                st.success(f"¡Venta registrada con éxito para {cliente}!")
                st.balloons()

# ---------------------------------------------------------
# TAB 2: PANEL DE MÉTRICAS DEL DÍA / MES
# ---------------------------------------------------------
with tabs[1]:
    st.header("Resumen de Ventas")
    
    conn = get_connection()
    df_ventas = pd.read_sql_query("SELECT * FROM ventas", conn)
    conn.close()

    if df_ventas.empty:
        st.info("Todavía no hay ventas registradas.")
    else:
        df_ventas['fecha_dt'] = pd.to_datetime(df_ventas['fecha'])
        df_ventas['fecha_dia'] = df_ventas['fecha_dt'].dt.date

        hoy = datetime.now().date()
        ventas_hoy = df_ventas[df_ventas['fecha_dia'] == hoy]

        # Métricas de Hoy
        st.subheader("📆 Rendimiento de Hoy")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Ventas Hoy", len(ventas_hoy))
        col_m2.metric("Unidades", int(ventas_hoy['cantidad'].sum()) if not ventas_hoy.empty else 0)
        col_m3.metric("Total USD", f"${ventas_hoy['total_usd'].sum():.2f}")

        st.divider()

        # Métricas Totales / Históricas
        st.subheader("📊 Histórico Acumulado")
        col_t1, col_t2 = st.columns(2)
        col_t1.metric("Total Recaudado", f"${df_ventas['total_usd'].sum():.2f} USD")
        col_t2.metric("Total Perfumes Vendidos", int(df_ventas['cantidad'].sum()))

        # Perfumes Más Vendidos
        st.subheader("🏆 Top Perfumes Más Vendidos")
        top_prods = df_ventas.groupby("producto")["cantidad"].sum().reset_index()
        top_prods = top_prods.sort_values(by="cantidad", ascending=False).head(5)
        st.dataframe(top_prods, use_container_width=True)

        st.subheader("📋 Últimas Ventas")
        st.dataframe(df_ventas.sort_values(by="id", ascending=False)[['fecha', 'cliente', 'producto', 'cantidad', 'total_usd', 'metodo_pago']], use_container_width=True)

# ---------------------------------------------------------
# TAB 3: IMPORTAR CATÁLOGO DESDE EXCEL
# ---------------------------------------------------------
with tabs[2]:
    st.header("Cargar / Actualizar Catálogo desde Excel")
    st.write("Subí la planilla de tu catálogo en formato `.xlsx` para cargar o actualizar los perfumes y precios.")

    archivo_excel = st.file_uploader("Seleccionar Excel de Catálogo", type=["xlsx", "xls"])
    
    if archivo_excel is not None:
        try:
            df_subido = pd.read_excel(archivo_excel)
            st.write("Vista previa de los datos:")
            st.dataframe(df_subido.head(), use_container_width=True)

            if st.button("📥 Importar Perfumes al Sistema", type="primary"):
                conn = get_connection()
                c = conn.cursor()
                
                # Mapeo flexible de columnas
                count = 0
                for _, row in df_subido.iterrows():
                    marca = str(row.get('Marca', row.get('MARCA', 'Varios'))).strip()
                    tipo = str(row.get('Tipo / Género', row.get('Tipo', 'Unisex'))).strip()
                    producto = str(row.get('Nombre del Producto', row.get('Nombre', row.get('Producto', '')))).strip()
                    
                    precio_val = row.get('Precio USD', row.get('Precio (USD)', row.get('Precio', 0)))
                    try:
                        precio_usd = float(str(precio_val).replace('$', '').replace(',', '').strip())
                    except:
                        precio_usd = 0.0

                    if producto:
                        c.execute('''
                            INSERT INTO catalogo (marca, tipo, producto, precio_usd)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(producto) DO UPDATE SET
                                marca=excluded.marca,
                                tipo=excluded.tipo,
                                precio_usd=excluded.precio_usd
                        ''', (marca, tipo, producto, precio_usd))
                        count += 1

                conn.commit()
                conn.close()
                st.success(f"¡Se actualizaron {count} perfumes en el catálogo!")
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel: {e}")

# ---------------------------------------------------------
# TAB 4: EXPORTAR HISTORIAL DE VENTAS A EXCEL
# ---------------------------------------------------------
with tabs[3]:
    st.header("Descargar Reporte de Ventas")
    st.write("Generá y descargá una planilla Excel con todas las ventas registradas para tener de respaldo o compartir.")

    conn = get_connection()
    df_descarga = pd.read_sql_query("SELECT * FROM ventas", conn)
    conn.close()

    if df_descarga.empty:
        st.info("Aún no hay ventas para exportar.")
    else:
        # Convertir dataframe a archivo Excel en memoria
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_descarga.to_excel(writer, index=False, sheet_name='Ventas')
        excel_data = output.getvalue()

        st.download_button(
            label="📊 Descargar Ventas en Excel (.xlsx)",
            data=excel_data,
            file_name=f"Ventas_Landen_Store_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )