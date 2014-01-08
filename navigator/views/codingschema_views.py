from amcat.models import CodingSchema, authorisation, CodingSchemaField, CodingSchemaFieldType
import json
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView
from navigator.views.datatableview import DatatableMixin
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from api.rest.datatable import Datatable
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from api.rest.resources import CodingSchemaResource, CodingSchemaFieldResource
from amcat.models.project import LITTER_PROJECT_ID
from django.core.urlresolvers import reverse
from django.forms.widgets import HiddenInput
from amcat.models.coding import codingruletoolkit
from django.http import HttpResponse
from django import forms
from navigator.utils.misc import session_pop

class CodingSchemaListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, ListView):
    model = CodingSchema
    parent = ProjectDetailsView
    context_category = 'Coding'

    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaListView, self).get_context_data(**kwargs)
        owned_schemas = Datatable(CodingSchemaResource, rowlink='./{id}').filter(project=self.project)
        linked_schemas = (Datatable(CodingSchemaResource, rowlink='./{id}')
                        .filter(projects_set=self.project))
        
        ctx.update(locals())
        return ctx

class CodingSchemaDetailsView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, DetailView):
    model = CodingSchema
    parent = CodingSchemaListView
    context_category = 'Coding'
    resource = CodingSchemaFieldResource

    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaDetailsView, self).get_context_data(**kwargs)
        object = self.get_object()
        is_new=session_pop(self.request.session, "schema_{}_is_new".format(object.id), False)
        is_edited=session_pop(self.request.session, "schema_{}_edited".format(object.id), False)
        ctx.update(locals())
        return ctx

    def filter_table(self, table):
        return table.hide("codingschema")
        
class CodingSchemaDeleteView(ProjectViewMixin, HierarchicalViewMixin, RedirectView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "delete"
    model = CodingSchema
    
    def get_redirect_url(self, project_id, codingschema_id):
        schema = self.get_object()
        schema.project_id = LITTER_PROJECT_ID
        schema.save()
        self.request.session['deleted_schema'] = codingschema_id
        
        return reverse("coding schema-list", args=(project_id, ))

class CodingSchemaCreateView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, CreateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaListView
    url_fragment = "new"
    model = CodingSchema
        
    def get_form(self, form_class):
        form = super(CodingSchemaCreateView, self).get_form(form_class)
        form.fields["project"].widget = HiddenInput()
        form.fields["project"].initial = self.project
        form.fields["highlighters"].required = False
        return form

    def get_success_url(self):
        return reverse("coding schema-details", args=(self.project.id, self.object.id))

class CodingSchemaEditView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, UpdateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "edit"
    model = CodingSchema

    def get_success_url(self):
        return reverse("coding schema-details", args=(self.project.id, self.object.id))


class CodingSchemaEditFieldsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, TemplateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "fields"
    model = CodingSchema


    def get_context_data(self, **kwargs):
        ctx = super(CodingSchemaEditFieldsView, self).get_context_data(**kwargs)
        fields_null = dict([(f.name, f.null) for f in CodingSchemaField._meta.fields])
        rules_valid=json.dumps(codingruletoolkit.schemarules_valid(self.get_object()))
        ctx.update(locals())
        return ctx
    
    def get(self, *args, **kargs):
        if self.get_object().project != self.project:
            # Offer to copy it to currect project
            pass#return redirect(copy_schema, project.id, schema.id)
        return super(CodingSchemaEditFieldsView, self).get(*args, **kargs)

    def post(self, *args, **kargs):
        commit = self.request.GET.get("commit") in (True, "true")
        fields = json.loads(self.request.POST['fields'])
        schema = self.get_object()

        forms = list(self._get_schemafield_forms(fields))
        errors = dict(_get_form_errors(forms))

        if not errors and commit:
            fields = [form.save(commit=False) for form in forms]

            for i, field in enumerate(fields):
                field.fieldnr = (i+1) * 10
                field.save()

            for field in set(schema.fields.all()) - set(fields):
                # Remove deleted fields
                field.delete()

            self.request.session["schema_{}_edited".format(schema.id)] = True 

        # Always send response (don't throw an error)
        schema_url = reverse("coding schema-details", args=[self.project.id, schema.id])

        return HttpResponse(
            json.dumps({
                "fields" : errors, "schema_url" : schema_url,
                "rules_valid" : codingruletoolkit.schemarules_valid(schema)
            }),
            mimetype='application/json'
        )

    def _get_schemafield_forms(self, fields):
        schema = self.get_object()
        for field in fields:
            field["codingschema"] = schema.id
            instance = CodingSchemaFieldForm._meta.model.objects.get(id=field["id"]) if "id" in field else None
            yield CodingSchemaFieldForm(schema, data=field, instance=instance)

def _get_form_errors(forms):
    """
    Check each form for errors. If an error is found in a form, a tuple
    of the form:

      (fieldnr, errors_dict)

    is yielded.
    """
    return ((f.data.get('fieldnr') or f.data["label"], f.errors) for f in forms if not f.is_valid())
        
class CodingSchemaEditRulesView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, TemplateView):
    required_project_permission = authorisation.ROLE_PROJECT_WRITER
    parent = CodingSchemaDetailsView
    url_fragment = "rules"
    model = CodingSchema

    def get(self, *args, **kargs):
        if self.get_object().project != self.project:
            # Offer to copy it to currect project
            pass#return redirect(copy_schema, project.id, schema.id)
        return super(CodingSchemaEditFieldsView, self).get(*args, **kargs)

    


class CodingSchemaFieldForm(forms.ModelForm):
    label = forms.CharField()
    default = forms.CharField(required=False)

    def __init__(self, schema, *args, **kwargs):
        super(CodingSchemaFieldForm, self).__init__(*args, **kwargs)
        self.fields['codebook'].required = False
        self.fields['codebook'].queryset = schema.project.get_codebooks()

    def _to_bool(self, val):
        if val is None:
            return 

        if str(val).lower() in ("true", "1", "yes"):
            return True
        elif str(val).lower() in ("false", "0", "no"):
            return False

    def clean_codebook(self):
        db_type = CodingSchemaFieldType.objects.get(name__iexact="Codebook")

        if 'fieldtype' not in self.cleaned_data:
            raise ValidationError("Fieldtype must be set in order to check this field")
        elif self.cleaned_data['fieldtype'] == db_type:
            if not self.cleaned_data['codebook']:
                raise ValidationError("Codebook must be set when fieldtype is '{}'".format(db_type))
        elif self.cleaned_data['codebook']:
            raise ValidationError("Codebook must not be set when fieldtype is '{}'".format(self.cleaned_data['fieldtype']))

        return self.cleaned_data['codebook']

    def clean_default(self):
        # Differentiate between '' and None
        value = self.cleaned_data['default']

        if 'fieldtype' not in self.cleaned_data:
            raise ValidationError("Fieldtype must be set in order to check this field")

        if self.data['default'] is None:
            return 

        # Fieldtype is set
        fieldtype = self.cleaned_data['fieldtype']
        if fieldtype.serialiserclass == BooleanSerialiser:
            value = self._to_bool(value)

            if value is None:
                raise ValidationError(
                    ("When fieldtype is of type {}, default needs " + 
                    "to be empty, true or false.").format(fieldtype))

        serialiser = fieldtype.serialiserclass(CodingSchemaField(**self.cleaned_data))

        try:
            return serialiser.serialise(value)
        except:
            if fieldtype.serialiserclass == CodebookSerialiser:
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError("This value needs to be a code_id.")

                # possible_values doesn't return a queryset, so we need to iterate :(
                if value in (code.id for code in serialiser.possible_values):
                    return value

                raise ValidationError("'{}' is not a valid value.".format(value))

            # Can't catch specific error
            possible_values = serialiser.possible_values

            if possible_values is not None:
                raise ValidationError(
                    "'{}' is not a valid value. Options: {}".format(
                        self.cleaned_data['default'], possible_values
                    )
                )

            raise ValidationError("'{}' is not a valid value".format(value))

        return value

    class Meta:
        model = CodingSchemaField
