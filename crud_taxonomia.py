import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import warnings
import pandas as pd
from functools import partial
warnings.filterwarnings('ignore')

#################################################################
# Verifique se já existe um app inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate('apontamento_horas.json')
    firebase_admin.initialize_app(cred)

# Conectar ao Firestore
db = firestore.client()
################################################################



# 1. I'll need a function to read the collection and bring me the document given a client name

def get_document_by_specific_parameter(collection_name: str,
                                       field: str,
                                       field_value: str) -> dict:

    collection = db.collection(collection_name)
    
    documents_list = collection.where(field, '==', field_value).stream()
    
    results = [document.to_dict() for document in documents_list]
    
    return results[0]

get_field_list = lambda collection_name, field, field_value, parameter_name: get_document_by_specific_parameter(collection_name, field, field_value)[parameter_name]

#1. #########################################################################################################

#2. I'll need a function to list the key that is my index in that collection

get_list_of_unique_index = lambda collection_name, field: list(set([document.to_dict()[field] for document in db.collection(collection_name).stream() if field in document.to_dict()])) 

#############################################################################################################

#3. Function to update specific document field
def update_specific_document_field(collection_name, document_id, field, value):
    try:
        
    # Acessa o documento específico dentro da coleção
        documento_ref = db.collection(collection_name).document(document_id)

    # Atualiza o campo com o novo valor
        documento_ref.update({field: value})

        return True
    except:
        return False

def update_document_by_id(collection_name, doc_id, updated_data):
    try:

        # Referência para o documento específico na coleção
        doc_ref = db.collection(collection_name).document(doc_id)

        # Atualiza os campos do documento com os dados passados
        doc_ref.set(updated_data)

        return True

    except:
        return False


####################################################################
# 4. Function to get the index by a specific field and value

def find_id_by_field_value(collection_name, field, value):
    data_structure = {document.id: document.to_dict()
        for document in db.collection(collection_name).stream()}
    
    return next(
        (id for id, document in data_structure.items() if document.get(field) == value),
        None
    )
# 5. Function to add a document in a collection

def create_document(collection_name: str, item: dict):
    
    collection_ref = db.collection(collection_name)

    try:
        doc_ref = collection_ref.add(item)
        return True
    
    except:
        return False

def delete_document(collection_name: str, document_id: str):
    doc_ref = db.collection(collection_name).document(document_id)
    try:
        doc_ref.delete()
        return True
    except:
        return False

def return_field_values_by_key(collection_name, field, value, key):

    data_structure = {document.id: document.to_dict()
        for document in db.collection(collection_name).stream()}
    
    result_list = [
        document.get(key) for id, document in data_structure.items() if document.get(field) == value
    ]


    return result_list 

get_documents_ids_by_specific_user = lambda collection_name, user_name: [document.id for document in db.collection(collection_name).where("usuario", '==', user_name).stream()]
get_documents_ids_by_specific_user_period = lambda collection_name, user_name, period: [document.id for document in db.collection(collection_name).where("usuario", '==', user_name).where("periodo", '==', period).stream()]
generate_filtered_dataframe_by_period = lambda pandas_dataframe, period_column, period: pandas_dataframe[pandas_dataframe[period_column] == period]



def generate_dataframe_by_firebase_collection_filtered_by_user(collection_name: str,
                                   list_of_attributes: list,
                                   user: str):
    
    
    get_list_attribute = partial(return_field_values_by_key, collection_name,
                                 "usuario",
                                 user)
    
    list_of_lists = [get_list_attribute(attrib) for attrib in list_of_attributes]

    max_list_lenght = max([len(attrib) for attrib in list_of_lists])

    adjusted_data_structure = {attrib: get_list_attribute(attrib) + 
                               [None for _ in range(max_list_lenght-len(get_list_attribute(attrib)))]
                               for attrib in list_of_attributes}
    
    pandas_dataframe = pd.DataFrame(adjusted_data_structure, index=get_documents_ids_by_specific_user(collection_name, user))

    return pandas_dataframe

def return_dataframe_adjustments_and_removed_itens(df_original: pd.DataFrame,
                                                   df_adjusted: pd.DataFrame) -> list:
    df_original_dict = df_original.to_dict('index')
    df_adjusted_dict = df_adjusted.to_dict('index')
    
    def removed_itens(df_original: pd.DataFrame, df_adjusted: pd.DataFrame) -> list:
        return [index for index in list(df_original.index) if index not in list(df_adjusted.index)]
    
    def return_dict_data_adjustments(dict_original:dict,
                                 dict_adjusted: dict ) -> dict:
    
        ids_to_check = [key for key, value in dict_adjusted.items()] 
    
        list_to_return = {id: dict_adjusted.get(id) for id in ids_to_check if dict_original.get(id) != dict_adjusted.get(id)}  

        return list_to_return if list_to_return != [{}] else None
    
    return [return_dict_data_adjustments(df_original_dict, df_adjusted_dict),removed_itens(df_original, df_adjusted)]
    

def delete_doc_by_id(collection_name: str, doc_id: str):
    try:
        db.collection(collection_name).document(doc_id).delete()
        return True
    except:
        return False


update_documents_from_adjusted_return = lambda adjusted_dataframe_return: [update_document_by_id("registros", key, value) for key, value in adjusted_dataframe_return.items()]
remove_documents_from_adjusted_return = lambda documents_list: [delete_doc_by_id("registros", doc) for doc in documents_list]


def main():
    st.title("CRUD de Taxonomias")

    # Sidebar para seleção de operações
    operation = st.sidebar.selectbox("Selecione a operação desejada", ["Cadastrar", "Visualizar/Alterar", "Excluir", "Cadastro de Usuários"],
                                     placeholder="Selecione uma operação",
                                     index=None)

    match operation:
        case "Cadastrar":
            cadastrar_taxonomia()
        case "Visualizar/Alterar":
            visualizar_alterar_taxonomia()
        case "Excluir":
            excluir_taxonomia()
        case "Cadastro de Usuários":
            cadastrar_usuarios()
        case _:
            tela_inicial()

def cadastrar_taxonomia():
    st.header("Cadastrar Nova Taxonomia")
    
    cliente = st.text_input("Cliente")
    projetos_atividades = st.text_area("Projetos/Atividades (um por linha)")
    tipo = st.text_area("Tipo (um por linha)")
    detalhe = st.text_area("Detalhe (um por linha)")

    if st.button("Cadastrar"):   
        document = {
            "cliente": cliente,
            "projetos_atividades": projetos_atividades.split("\n"),
            "tipo": tipo.split("\n"),
            "detalhe": detalhe.split("\n")
        }

        if create_document("taxonomia", document):
            st.success("Taxonomia cadastrada com sucesso!", icon="✅")
            st.toast("Taxonomia cadastrada com sucesso!")
        else:
            st.error('Erro ao cadastrar Taxonomia', icon="🚨")
            st.toast("Erro ao cadastrar Taxonomia, tente novamente")


def visualizar_alterar_taxonomia():
    
    st.header("Visualizar/Alterar Taxonomia")

    # Selecionar taxonomia para visualizar/alterar
    selected_id = st.selectbox("Selecione a taxonomia para visualizar ou alterar", 
        options=get_list_of_unique_index("taxonomia", "cliente"),
        index=None,
        placeholder="Selecione")

    if selected_id:
        id_to_update = find_id_by_field_value("taxonomia", "cliente", selected_id)

        cliente = st.text_input("Cliente", value=selected_id)
        projetos_atividades = st.text_area("Projetos (um por linha)", value="\n".join(get_field_list("taxonomia", "cliente", selected_id, "projetos_atividades")))
        tipo = st.text_area("Tipo (um por linha)", value="\n".join(get_field_list("taxonomia", "cliente", selected_id, "tipo")))
        detalhe = st.text_area("Detalhe (um por linha)", value="\n".join(get_field_list("taxonomia", "cliente", selected_id, "detalhe")))

        if st.button("Atualizar"):
            document = {
            "cliente": cliente,
            "projetos_atividades": projetos_atividades.split("\n"),
            "tipo": tipo.split("\n"),
            "detalhe": detalhe.split("\n")
            }
            
            if update_document_by_id("taxonomia", id_to_update, document):
                st.success("Taxonomia atualizada com sucesso!")
                st.toast("Taxonomia atualizada com sucesso!")
            else:
                st.error('Erro ao atualizar Taxonomia', icon="🚨")
                st.toast("Erro ao atualizar Taxonomia")


def excluir_taxonomia():
    st.header("Excluir Taxonomia")

    # Selecionar taxonomia para excluir
    selected_id = st.selectbox("Selecione a taxonomia para excluir", 
        options=get_list_of_unique_index("taxonomia", "cliente"),
        index=None,
        placeholder="Selecione")

    if selected_id:
        id_to_update = find_id_by_field_value("taxonomia", "cliente", selected_id)
        
        if delete_document("taxonomia", id_to_update):
            st.success("Taxonomia excluída com sucesso!")
            st.toast("Taxonomia excluída com sucesso!")
        else:
            st.error('Erro ao excluir Taxonomia', icon="🚨")
            st.toast("Erro ao excluir Taxonomia!")
def cadastrar_usuarios():

    st.title("Cadastro de usuários")



    with st.spinner("Em progresso"):

        with st.form("Fazer cadastro de usuário",
                     clear_on_submit=True):
            st.write("Adicionar Usuário")
            
            novo_nome = st.text_input("Nome")
            
            time = get_list_of_unique_index("usuarios", "time")
            novo_time = st.selectbox("Time", time, key="time", placeholder="", index=None)

            submitted = st.form_submit_button("Adicionar Usuário")
            
            if submitted:
                register = {
                    'nome': novo_nome,
                    'time': novo_time,
                    'usuario': 'admin'
                }
                
                # Exibe o botão para limpar os campos após a inclusão
                create_document("usuarios", register)
                st.warning("Registro incluído com sucesso")

                with st.spinner("Em progresso"):
                    st.session_state["pandas_dataframe_tabela_usuarios"] = generate_dataframe_by_firebase_collection_filtered_by_user("usuarios", ["nome", "time"],"admin")
                    st.markdown(f"<h3 style='text-align: left; color: #4169E1;'>Apenas Visualização! Funcionalidade de edição em Construção</h3>", unsafe_allow_html=True)
                    edited_df_usuarios = st.data_editor(st.session_state["pandas_dataframe_tabela_usuarios"], num_rows="dynamic", hide_index=True)

                    if not edited_df_usuarios.equals(st.session_state["pandas_dataframe_tabela_usuarios"]):
                
                        updated = return_dataframe_adjustments_and_removed_itens(st.session_state["pandas_dataframe_usuario_periodo"],
                                      edited_df_usuarios)
                
                        updated_with_usuario = {key: {**value, 'usuario': 'admin'} for key, value in updated[0].items()}
                        removed_documents = updated[1]


                        update_documents_from_adjusted_return(updated_with_usuario)

                        if removed_documents != []:
                            remove_documents_from_adjusted_return(removed_documents)


def tela_inicial():
    st.header("Tela Inicial")


if __name__ == "__main__":
    main()