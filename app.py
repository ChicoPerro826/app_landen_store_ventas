import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Landen Store - Control de Ventas", page_icon="🧴", layout="centered")

# --- CONEXIÓN Y CREACIÓN DE BASE DE DATOS ---
def get_connection():
    return sqlite3.connect("landen_store.db")

def init_sqlite():
    conn = get_connection()
    c = conn.cursor()
    # Tabla de Catálogo con Costos y Precios
    c.execute('''
        CREATE TABLE IF NOT EXISTS catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT,
            tipo TEXT,
            producto TEXT UNIQUE,
            costo_usd REAL,
            precio_usd REAL
        )
    ''')
    # Tabla de Ventas con Ganancia
    c.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            marca TEXT,
            producto TEXT,
            cliente TEXT,
            tipo_cliente TEXT,
            cantidad INTEGER,
            costo_unitario_usd REAL,
            precio_unitario_usd REAL,
            total_usd REAL,
            ganancia_usd REAL,
            metodo_pago TEXT,
            notas TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_sqlite()

# --- ENCABEZADO Y PESTAÑAS ---
st.title("🧴 Landen Store")
st.caption("Gestión de Ventas & Control de Ganancias")

tabs = st.tabs(["🛒 Nueva Venta", "📊 Panel & Ganancias", "📦 Catálogo / Excel", "📥 Exportar Ventas"])

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
        marcas = sorted(df_cat['marca'].dropna().unique().tolist())
        marca_sel = st.selectbox("Marca", marcas)

        prods_marca = df_cat[df_cat['marca'] == marca_sel]
        prod_names = sorted(prods_marca['producto'].dropna().unique().tolist())
        producto_sel = st.selectbox("Producto / Perfume", prod_names)

        # Obtener costo y precio de venta sugerido
        prod_info = prods_marca[prods_marca['producto'] == producto_sel].iloc[0]
        costo_sugerido = float(prod_info.get('costo_usd', 0.0) or 0.0)
        precio_sugerido = float(prod_info.get('precio_usd', 0.0) or 0.0)

        col1, col2 = st.columns(2)
        with col1:
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
        with col2:
            precio_unitario = st.number_input("Precio de Venta Unitario ($ USD)", value=precio_sugerido, step=1.0)

        # Mostrar costo unitario y ganancia estimada por unidad
        ganancia_unitaria = precio_unitario - costo_sugerido
        total_venta = cantidad * precio_unitario
        total_ganancia = cantidad * ganancia_unitaria

        st.info(f"💵 **Total cobrado:** ${total_venta:.2f} USD | 📈 **Ganancia neta:** ${total_ganancia:.2f} USD")

        st.divider()

        cliente = st.text_input("Nombre del Cliente", placeholder="Ej: Lucas")
        tipo_cliente = st.radio("Tipo de Cliente", ["Minorista", "Mayorista"], horizontal=True)
        metodo_pago = st.selectbox("Método de Pago", ["Efectivo USD", "Efectivo ARS", "Transferencia", "Mercado Pago", "Otro"])
        notas = st.text_input("Notas / Observaciones", placeholder="Opcional (ej: precio especial, seña)")

        if st.button("✅ Registrar Venta", type="primary", use_container_width=True):
            if not cliente.strip():
                st.error("Por favor ingresá el nombre del cliente.")
            else:
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO ventas (fecha, marca, producto, cliente, tipo_cliente, cantidad, costo_unitario_usd, precio_unitario_usd, total_usd, ganancia_usd, metodo_pago, notas)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fecha_actual, marca_sel, producto_sel, cliente, tipo_cliente, cantidad, costo_sugerido, precio_unitario, total_venta, total_ganancia, metodo_pago, notas))
                conn.commit()
                conn.close()
                st.success(f"¡Venta registrada con éxito para {cliente}! Ganancia: ${total_ganancia:.2f} USD")
                st.balloons()

# ---------------------------------------------------------
# TAB 2: PANEL DE MÉTRICAS Y GANANCIAS
# ---------------------------------------------------------
with tabs[1]:
    st.header("Resumen de Ventas y Rendimiento")
    
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
        col_h1, col_h2, col_h3 = st.columns(3)
        col_h1.metric("Ventas Hoy", len(ventas_hoy))
        col_h2.metric("Facturado Hoy", f"${ventas_hoy['total_usd'].sum():.2f} USD")
        col_h3.metric("Ganancia Hoy", f"${ventas_hoy['ganancia_usd'].sum():.2f} USD")

        st.divider()

        # Métricas Totales
        st.subheader("📊 Histórico Acumulado")
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Total Facturado", f"${df_ventas['total_usd'].sum():.2f} USD")
        col_t2.metric("Ganancia Neta Total", f"${df_ventas['ganancia_usd'].sum():.2f} USD")
        col_t3.metric("Perfumes Vendidos", int(df_ventas['cantidad'].sum()))

        st.divider()

        # Top Perfumes
        st.subheader("🏆 Top Perfumes Más Vendidos")
        top_prods = df_ventas.groupby("producto").agg(
            Unidades_Vendidas=('cantidad', 'sum'),
            Total_Facturado=('total_usd', 'sum'),
            Ganancia_Total=('ganancia_usd', 'sum')
        ).reset_index().sort_values(by="Unidades_Vendidas", ascending=False).head(5)

        st.dataframe(top_prods, use_container_width=True)

        st.subheader("📋 Últimas Ventas")
        st.dataframe(
            df_ventas.sort_values(by="id", ascending=False)[
                ['fecha', 'cliente', 'producto', 'cantidad', 'total_usd', 'ganancia_usd', 'metodo_pago']
            ], 
            use_container_width=True
        )

# ---------------------------------------------------------
# TAB 3: IMPORTAR CATÁLOGO DESDE EXCEL
# ---------------------------------------------------------
with tabs[2]:
    st.header("Cargar / Actualizar Catálogo")
    st.write("Subí tu planilla Excel para actualizar los perfumes, costos y precios de venta.")

    archivo_excel = st.file_uploader("Seleccionar Excel de Catálogo", type=["xlsx", "xls"])
    
    if archivo_excel is not None:
        try:
            # Si tiene varias hojas, permitimos seleccionar la hoja
            xls = pd.ExcelFile(archivo_excel)
            hoja_sel = st.selectbox("Seleccionar hoja del Excel", xls.sheet_names)
            df_subido = pd.read_excel(archivo_excel, sheet_name=hoja_sel)

            st.write("Vista previa de los datos:")
            st.dataframe(df_subido.head(), use_container_width=True)

            if st.button("📥 Importar / Actualizar Catálogo", type="primary"):
                conn = get_connection()
                c = conn.cursor()
                
                count = 0
                for _, row in df_subido.iterrows():
                    marca = str(row.get('Marca', row.get('MARCA', 'Varios'))).strip()
                    tipo = str(row.get('Tipo / Género', row.get('Tipo', 'Unisex'))).strip()
                    producto = str(row.get('Nombre del Producto', row.get('Nombre', row.get('Producto', '')))).strip()
                    
                    # Extraer Costo y Precio de Venta
                    costo_val = row.get('Precio (USD)', row.get('Precio Costo USD', row.get('Costo', 0)))
                    precio_val = row.get('Precio USD', row.get('Precio Venta USD', row.get('Precio', 0)))

                    try:
                        costo_usd = float(str(costo_val).replace('$', '').replace(',', '').strip())
                    except:
                        costo_usd = 0.0

                    try:
                        precio_usd = float(str(precio_val).replace('$', '').replace(',', '').strip())
                    except:
                        precio_usd = 0.0

                    if producto and producto.lower() != 'nan':
                        c.execute('''
                            INSERT INTO catalogo (marca, tipo, producto, costo_usd, precio_usd)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(producto) DO UPDATE SET
                                marca=excluded.marca,
                                tipo=excluded.tipo,
                                costo_usd=excluded.costo_usd,
                                precio_usd=excluded.precio_usd
                        ''', (marca, tipo, producto, costo_usd, precio_usd))
                        count += 1

                conn.commit()
                conn.close()
                st.success(f"¡Se cargaron/actualizaron {count} perfumes exitosamente!")
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel: {e}")

# ---------------------------------------------------------
# TAB 4: EXPORTAR REPORTE COMPLETO
# ---------------------------------------------------------
with tabs[3]:
    st.header("Descargar Reporte de Ventas")
    
    conn = get_connection()
    df_descarga = pd.read_sql_query("SELECT * FROM ventas", conn)
    conn.close()

    if df_descarga.empty:
        st.info("Aún no hay ventas para exportar.")
    else:
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_descarga.to_excel(writer, index=False, sheet_name='Ventas')
        excel_data = output.getvalue()

        st.download_button(
            label="📊 Descargar Historial Completo (.xlsx)",
            data=excel_data,
            file_name=f"Reporte_Ventas_Landen_Store_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )