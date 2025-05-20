from flask import Flask, request, render_template, jsonify
import pandas as pd
import math
import os

EXCEL_FILE = "cable_cobre.xlsx"

app = Flask(__name__)

def cargar_dataframe():
    try:
        try:
            df = pd.read_excel(EXCEL_FILE, engine='xlrd')
        except Exception:
            df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        required_columns = ['AWG', 'Diametro_mm', 'AT_cuadrado', 'I60', 'I75', 'I90']
        if not all(col in df.columns for col in required_columns):
            return None, f"Faltan columnas requeridas: {required_columns}"
        df['Diametro_mm'] = pd.to_numeric(df['Diametro_mm'], errors='coerce')
        df['AT_cuadrado'] = pd.to_numeric(df['AT_cuadrado'], errors='coerce')
        df['I60'] = pd.to_numeric(df['I60'], errors='coerce')
        df['I75'] = pd.to_numeric(df['I75'], errors='coerce')
        df['I90'] = pd.to_numeric(df['I90'], errors='coerce')
        df.dropna(subset=['Diametro_mm', 'AT_cuadrado', 'I60', 'I75', 'I90'], inplace=True)
        df['AWG'] = df['AWG'].astype(str).str.strip()
        return df, None
    except Exception as e:
        return None, str(e)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/consulta", methods=["POST"])
def consulta():
    data = request.json
    modo = data.get("modo")
    valor = data.get("valor")
    df, error = cargar_dataframe()
    if error:
        return jsonify({"error": error}), 400
    if modo == "diametro":
        try:
            dato_usuario = float(valor)
            if dato_usuario <= 0:
                return jsonify({"error": "El diámetro debe ser positivo."}), 400
        except ValueError:
            return jsonify({"error": "El diámetro debe ser un número."}), 400

        found_row = None
        exact_diameter_rows = df[df['Diametro_mm'] == dato_usuario]
        if not exact_diameter_rows.empty:
            found_row = exact_diameter_rows.iloc[0]
            mensaje = f"Coincidencia exacta de Diámetro ({dato_usuario} mm) encontrada."
        else:
            calculated_area = math.pi * (dato_usuario / 4)**2
            exact_area_rows = df[df['AT_cuadrado'].round(4) == round(calculated_area, 4)]
            if not exact_area_rows.empty:
                found_row = exact_area_rows.iloc[0]
                mensaje = f"Coincidencia exacta de Área ({calculated_area:.4f} mm²) encontrada."
            else:
                df_sorted = df.sort_values(by='AT_cuadrado').copy()
                greater_area_rows = df_sorted[df_sorted['AT_cuadrado'] > calculated_area]
                if not greater_area_rows.empty:
                    found_row = greater_area_rows.iloc[0]
                    mensaje = f"Área aproximada. Se encontró el siguiente valor mayor ({found_row['AT_cuadrado']:.4f} mm²)."
                else:
                    return jsonify({"error": "No se encontró ningún valor de AT_cuadrado mayor que el ingresado."}), 404
        if found_row is not None:
            return jsonify({
    "mensaje": mensaje,
    "AWG": str(found_row.get("AWG", "N/D")),
    "I60": str(found_row.get("I60", "N/D")),
    "I75": str(found_row.get("I75", "N/D")),
    "I90": str(found_row.get("I90", "N/D"))
})
        else:
            return jsonify({"error": "No se pudo encontrar un conductor coincidente."}), 404

    elif modo == "awg":
        awg2 = str(valor).strip()
        awg_rows = df[df['AWG'] == awg2]
        if not awg_rows.empty:
            found_row = awg_rows.iloc[0]
            return jsonify({
                "mensaje": f"AWG '{awg2}' encontrado.",
                "AWG": str(found_row.get("AWG", "N/D")),
                "I60": str(found_row.get("I60", "N/D")),
                "I75": str(found_row.get("I75", "N/D")),
                "I90": str(found_row.get("I90", "N/D"))
            })
        else:
            return jsonify({"error": f"AWG '{awg2}' no encontrado."}), 404
    else:
        return jsonify({"error": "Modo inválido."}), 400

if __name__ == "__main__":
    app.run(debug=True)
